import json
from time import sleep

import dateparser
import reversion
from dateutil.relativedelta import relativedelta
from django.db.models import Min, F
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from reversion.views import create_revision

from core.logic.dates import month_start, month_end
from core.models import UL_CONS_STAFF, REL_ORG_ADMIN
from core.permissions import (
    SuperuserOrAdminPermission,
    OrganizationRelatedPermissionMixin,
)
from logs.views import StandardResultsSetPagination
from organizations.logic.queries import organization_filter_from_org_id
from .models import (
    SushiCredentials,
    CounterReportType,
    SushiFetchAttempt,
    CounterReportsToCredentials,
)
from .serializers import (
    CounterReportTypeSerializer,
    SushiCredentialsSerializer,
    SushiCredentialsDataSerializer,
    SushiFetchAttemptSerializer,
    SushiFetchAttemptSimpleSerializer,
    UnsetBrokenSerializer,
)
from .tasks import (
    run_sushi_fetch_attempt_task,
    fetch_new_sushi_data_task,
    fetch_new_sushi_data_for_credentials_task,
)


class SushiCredentialsViewSet(ModelViewSet):

    serializer_class = SushiCredentialsSerializer
    queryset = SushiCredentials.objects.none()

    def get_queryset(self):
        user_organizations = self.request.user.accessible_organizations()
        qs = SushiCredentials.objects.filter(organization__in=user_organizations)
        organization_id = self.request.query_params.get('organization')
        if organization_id:
            qs = qs.filter(**organization_filter_from_org_id(organization_id, self.request.user))
        # platform filter
        platform_id = self.request.query_params.get('platform')
        if platform_id:
            qs = qs.filter(platform_id=platform_id)
        qs = qs.prefetch_related('counterreportstocredentials_set__counter_report').select_related(
            'organization', 'platform', 'platform__source'
        )
        # we add info about locked status for current user
        org_to_level = {}
        for sc in qs:  # type: SushiCredentials
            if sc.organization_id not in org_to_level:
                org_to_level[sc.organization_id] = self.request.user.organization_relationship(
                    sc.organization_id
                )
            user_org_level = org_to_level[sc.organization_id]
            if user_org_level >= sc.lock_level:
                sc.locked_for_me = False
            else:
                sc.locked_for_me = True
            if user_org_level >= UL_CONS_STAFF:
                sc.can_lock = True
            else:
                sc.can_lock = False
        return qs

    @method_decorator(create_revision())
    def update(self, request, *args, **kwargs):
        reversion.set_comment('Updated through API')
        return super().update(request, *args, **kwargs)

    @method_decorator(create_revision())
    def create(self, request, *args, **kwargs):
        reversion.set_comment('Created through API')
        return super().create(request, *args, **kwargs)

    @method_decorator(create_revision())
    def destroy(self, request, *args, **kwargs):
        credentials = self.get_object()  # type: SushiCredentials
        if credentials.can_edit(request.user):
            reversion.set_comment('Deleted through API')
            return super().destroy(request, *args, **kwargs)
        else:
            raise PermissionDenied('User is not allowed to delete this object')

    @action(detail=True, methods=['post'], permission_classes=[SuperuserOrAdminPermission])
    def lock(self, request, pk=None):
        """
        Custom action to lock the SushiCredentials
        """
        credentials = get_object_or_404(SushiCredentials, pk=pk)
        owner_level = request.user.organization_relationship(credentials.organization_id)
        requested_level = request.data.get('lock_level', owner_level)
        credentials.change_lock(request.user, requested_level)
        return Response(
            {
                'ok': True,
                'lock_level': credentials.lock_level,
                'locked': credentials.lock_level >= UL_CONS_STAFF,
            }
        )

    @action(
        detail=True,
        methods=['post'],
        url_path="unset-broken",
        serializer_class=UnsetBrokenSerializer,
    )
    def unset_broken(self, request, pk):
        """
        Custom action to unset that SushiCredentials are broken
        """
        credentials = get_object_or_404(SushiCredentials, pk=pk)

        request_serializer = UnsetBrokenSerializer(instance=credentials, data=dict(request.data))
        request_serializer.is_valid(raise_exception=True)

        if 'counter_reports' in request_serializer.validated_data:
            for cr2c in CounterReportsToCredentials.objects.filter(
                credentials=credentials,
                counter_report__in=request_serializer.validated_data['counter_reports'],
            ):
                cr2c.unset_broken()
        else:
            credentials.unset_broken()
            for cr2c in CounterReportsToCredentials.objects.filter(credentials=credentials):
                cr2c.unset_broken()
        credentials.refresh_from_db()
        return Response(SushiCredentialsSerializer(credentials).data)

    @action(
        detail=True,
        methods=['get'],
        url_path="data",
        serializer_class=SushiCredentialsDataSerializer,
    )
    def data(self, request, pk):
        """ Display data for given set of credentials """
        credentials = get_object_or_404(SushiCredentials, pk=pk)

        # TODO perhaps we might add some year filter here

        current_time = timezone.now()
        start_year = (
            credentials.sushifetchattempt_set.aggregate(min_start=Min('start_date'))["min_start"]
            or current_time
        ).year
        end_year = current_time.year

        report_types_and_broken = [
            (e.counter_report, e.is_broken())
            for e in credentials.counterreportstocredentials_set.all().select_related(
                'counter_report'
            )
        ]
        report_types = [e[0] for e in report_types_and_broken]

        result = {}
        # initialize matrix with empty values
        for year in range(start_year, end_year + 1):
            year_result = {"year": year}
            for i in range(1, 13):
                year_result[f"{i:02d}"] = {
                    rt.code: {
                        "status": "untried",
                        "planned": False,
                        "broken": broken,
                        "counter_report": {"id": rt.pk, "name": rt.name, "code": rt.code,},
                    }
                    for (rt, broken) in report_types_and_broken
                }
            result[year] = year_result

        # update planned
        for intention in credentials.fetchintention_set.filter(
            counter_report__in=report_types, when_processed__isnull=True,
        ).select_related('counter_report'):
            start = intention.start_date
            end = intention.end_date
            report_type = intention.counter_report.code

            # iterate through months
            while start <= end:
                if start.year in result:
                    result[start.year][f"{start.month:02d}"][report_type]["planned"] = True
                start += relativedelta(months=1)

        # iterate through attempts
        for attempt in credentials.sushifetchattempt_set.filter(
            counter_report__in=report_types
        ).select_related('counter_report'):
            start = attempt.start_date
            end = attempt.end_date
            report_type = attempt.counter_report.code
            status = attempt.status

            # iterate through months
            while start <= end:
                if start.year in result:
                    before = result[start.year][f"{start.month:02d}"][report_type]["status"]
                    if status in ['FAILURE', 'BROKEN'] and before in ["untried"]:
                        # untried => failed
                        result[start.year][f"{start.month:02d}"][report_type]["status"] = "failed"
                    elif status == "PARTIAL_DATA" and before in [
                        "untried",
                        "failed",
                        "success",
                        "no_data",
                    ]:
                        # success. failed, success, no_data => partial_data
                        result[start.year][f"{start.month:02d}"][report_type][
                            "status"
                        ] = "partial_data"
                    elif status in ['NO_DATA'] and before in ["untried", "failed", "partial_data"]:
                        # failed, untried, partial_data => no_data
                        result[start.year][f"{start.month:02d}"][report_type]["status"] = "no_data"
                    elif status == 'SUCCESS' and before in [
                        "untried",
                        "failed",
                        "no_data",
                        "partial_data",
                    ]:
                        # failed, untried, no_data, partial_data => success
                        result[start.year][f"{start.month:02d}"][report_type]["status"] = "success"
                start += relativedelta(months=1)

        # reformat for serializer (dict => list)
        reformatted = list(result.values())
        for year_result in reformatted:
            for i in range(1, 13):
                key = f"{i:02d}"
                year_result[key] = sorted(
                    year_result[key].values(), key=lambda x: x["counter_report"]["id"]
                )

        serializer = SushiCredentialsDataSerializer(data=reformatted, many=True)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def count(self, request):
        """
        Just simple count of SushiCredentials
        """
        user_organizations = self.request.user.accessible_organizations()
        count = SushiCredentials.objects.filter(organization__in=user_organizations).count()
        broken = SushiCredentials.objects.filter(
            organization__in=user_organizations, broken__isnull=False
        ).count()
        broken_reports = CounterReportsToCredentials.objects.filter(
            credentials__organization__in=user_organizations, broken__isnull=False
        ).count()
        return Response({'count': count, 'broken': broken, 'broken_reports': broken_reports})

    @action(detail=False, methods=['get'], url_name='month-overview', url_path='month-overview')
    def month_overview(self, request):
        month = request.query_params.get('month')
        if not month:
            return Response(
                {'error': 'Missing "month" URL param'}, status=status.HTTP_400_BAD_REQUEST
            )

        month_date = dateparser.parse(month)
        start = month_start(month_date)
        end = month_end(month_date)
        credentials = self.get_queryset()
        enabled_attr = (
            {'credentials__enabled': True} if 'disabled' not in request.query_params else {}
        )
        query = (
            SushiFetchAttempt.objects.filter(
                start_date__lte=start,
                end_date__gte=end,
                credentials_id__in=credentials,
                in_progress=False,
                counter_report=F('credentials__counter_reports'),
                **enabled_attr,
            )
            .order_by("credentials_id", "counter_report_id", "-timestamp")
            .distinct("credentials_id", "counter_report_id")
            .select_related('credentials', 'counter_report')
        )
        records = SushiFetchAttemptSimpleSerializer(query, many=True).data
        return Response(records)


class CounterReportTypeViewSet(ReadOnlyModelViewSet):

    serializer_class = CounterReportTypeSerializer
    queryset = CounterReportType.objects.all()


class SushiFetchAttemptViewSet(ModelViewSet):

    serializer_class = SushiFetchAttemptSerializer
    queryset = SushiFetchAttempt.objects.none()
    http_method_names = ['get', 'post', 'options', 'head']
    pagination_class = StandardResultsSetPagination

    def get_object(self):
        return super().get_object()

    def get_queryset(self):
        organizations = self.request.user.accessible_organizations()
        filter_params = {}
        organization = self.request.query_params.get("organization")
        if organization and organization != "-1":
            filter_params['credentials__organization'] = get_object_or_404(
                organizations, pk=self.request.query_params['organization']
            )
        else:
            filter_params['credentials__organization__in'] = organizations
        if 'platform' in self.request.query_params:
            filter_params['credentials__platform_id'] = self.request.query_params['platform']
        if 'report' in self.request.query_params:
            filter_params['counter_report_id'] = self.request.query_params['report']
        if 'date_from' in self.request.query_params:
            date_from = dateparser.parse(self.request.query_params['date_from'])
            if date_from:
                filter_params['timestamp__date__gte'] = date_from
        if 'month' in self.request.query_params:
            month = self.request.query_params['month']
            filter_params['start_date__lte'] = month_start(dateparser.parse(month))
            filter_params['end_date__gte'] = month_start(dateparser.parse(month))
        if 'counter_version' in self.request.query_params:
            counter_version = self.request.query_params['counter_version']
            filter_params['credentials__counter_version'] = counter_version
        mode = self.request.query_params.get('mode')
        if mode == 'success_and_current':
            qs = SushiFetchAttempt.objects.current_or_successful()
        elif mode == 'current':
            qs = SushiFetchAttempt.objects.current()
        else:
            qs = SushiFetchAttempt.objects.all()

        # Show only latest in the chain
        qs = qs.last_queued()
        qs = qs.filter(**filter_params).select_related(
            'counter_report', 'credentials__organization', 'credentials__platform',
        )
        # ordering
        order_by = self.request.query_params.get('order_by')
        desc = self.request.query_params.get('desc', 'false')
        if order_by:
            prefix = '-' if desc == 'true' else ''
            qs = qs.order_by(prefix + order_by)
        return qs

    # TODO: is this still necessary? We do not seem to use it anymore from the UI
    def perform_create(self, serializer: SushiFetchAttemptSerializer):
        # check that the user is allowed to create attempts for this organization
        credentials = serializer.validated_data['credentials']
        counter_report = serializer.validated_data['counter_report']
        # check whether the credentials are not broken
        if (
            credentials.broken
            or credentials.counterreportstocredentials_set.filter(
                broken__isnull=False, counter_report=counter_report
            ).exists()
        ):
            raise ValidationError('Credentials seems to be broken.')

        org_relation = self.request.user.organization_relationship(credentials.organization_id)
        if org_relation < REL_ORG_ADMIN:
            raise PermissionDenied(
                'user is not allowed to start fetch attempts for this organization'
            )
        # proceed with creation
        serializer.validated_data['in_progress'] = True
        super().perform_create(serializer)
        attempt = serializer.instance
        attempt.triggered_by = self.request.user
        attempt.save()
        run_sushi_fetch_attempt_task.apply_async(args=(attempt.pk, True), countdown=1)


class StartFetchNewSushiDataTask(APIView):

    permission_classes = [SuperuserOrAdminPermission]

    def post(self, request):
        task = fetch_new_sushi_data_task.delay()
        return Response({'id': task.id,})


class StartFetchNewSushiDataForCredentialsTask(APIView):
    def post(self, request, credentials_pk):
        try:
            credentials = SushiCredentials.objects.get(pk=credentials_pk)
        except SushiCredentials.DoesNotExist:
            return HttpResponseBadRequest(
                json.dumps({'error': f'Credentials object with id={credentials_pk} does not exist'})
            )
        # let's check authorization
        if request.user.is_superuser or request.user.is_from_master_organization:
            pass
        elif OrganizationRelatedPermissionMixin.has_org_access(
            request.user, credentials.organization_id
        ):
            pass
        else:
            raise PermissionDenied('User is neither manager nor admin of related organization')
        task = fetch_new_sushi_data_for_credentials_task.delay(credentials.pk)
        return Response({'id': task.id,})
