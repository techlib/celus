import json
from datetime import timedelta
import typing

import dateparser
import reversion
from django.db.models import Count, Q, Max, Min, F
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from reversion.views import create_revision

from core.logic.dates import month_start, month_end
from core.logic.url import extract_field_from_request
from core.models import UL_CONS_STAFF, REL_ORG_ADMIN
from core.permissions import (
    SuperuserOrAdminPermission,
    OrganizationRelatedPermissionMixin,
    AdminAccessForOrganization,
)
from organizations.logic.queries import organization_filter_from_org_id
from sushi.models import CounterReportType, SushiFetchAttempt
from sushi.serializers import (
    CounterReportTypeSerializer,
    SushiFetchAttemptSerializer,
    SushiFetchAttemptSimpleSerializer,
)
from sushi.tasks import (
    run_sushi_fetch_attempt_task,
    fetch_new_sushi_data_task,
    fetch_new_sushi_data_for_credentials_task,
)
from .filters import CleanupFilterBackend
from .models import SushiCredentials
from .serializers import (
    SushiCredentialsSerializer,
    SushiCleanupSerializer,
    SushiCleanupCountSerializer,
)


class SushiCredentialsViewSet(ModelViewSet):

    serializer_class = SushiCredentialsSerializer
    queryset = SushiCredentials.objects.none()

    def get_queryset(self):
        user_organizations = self.request.user.accessible_organizations()
        qs = (
            SushiCredentials.objects.filter(organization__in=user_organizations)
            .select_related('organization', 'platform')
            .prefetch_related('active_counter_reports')
        )
        organization_id = self.request.query_params.get('organization')
        if organization_id:
            qs = qs.filter(**organization_filter_from_org_id(organization_id, self.request.user))
        # platform filter
        platform_id = self.request.query_params.get('platform')
        if platform_id:
            qs = qs.filter(platform_id=platform_id)
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

    @action(detail=False, methods=['get'])
    def count(self, request):
        """
        Just simple count of SushiCredentials
        """
        user_organizations = self.request.user.accessible_organizations()
        qs = SushiCredentials.objects.filter(organization__in=user_organizations)
        return Response({'count': qs.count(),})

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
        query = (
            SushiFetchAttempt.objects.filter(
                start_date=start, end_date=end, credentials_id__in=credentials, in_progress=False,
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
        return qs.filter(**filter_params).select_related(
            'counter_report', 'credentials__organization', 'credentials__platform',
        )

    @action(
        methods=['POST', 'GET'],
        detail=False,
        url_path='cleanup',
        serializer_class=SushiCleanupCountSerializer,
        filter_backends=(CleanupFilterBackend,),
        permission_classes=[AdminAccessForOrganization],
    )
    def cleanup(self, request):
        """
        Clean Sushi attempts (GET - just display the number POST - trigger deletion)

        keep only those which contain data and remove failures

        Return how many attempts (will be / were) deleted
        """
        queryset = self.filter_queryset(self.get_queryset())

        # apply organization filter if needed
        organization_id = extract_field_from_request(request, "organization")
        if organization_id and organization_id != -1:
            queryset = queryset.filter(credentials__organization_id=organization_id)

        pks = [
            e.pk
            for e in queryset.filter(import_batch__isnull=True)
            if e.status in ['FAILURE', 'BROKEN']
        ]

        if request.method == "POST":
            count, _ = SushiFetchAttempt.objects.filter(pk__in=pks).delete()
        elif request.method == "GET":
            count = SushiFetchAttempt.objects.filter(pk__in=pks).count()

        response_serializer = SushiCleanupCountSerializer(data={"count": count})
        response_serializer.is_valid(raise_exception=True)

        return Response(response_serializer.validated_data)

    def perform_create(self, serializer: SushiFetchAttemptSerializer):
        # check that the user is allowed to create attempts for this organization
        credentials = serializer.validated_data['credentials']
        org_relation = self.request.user.organization_relationship(credentials.organization_id)
        if org_relation < REL_ORG_ADMIN:
            raise PermissionDenied(
                'user is not allowed to start fetch attempts for this organization'
            )
        # proceed with creation
        serializer.validated_data['in_progress'] = True
        serializer.validated_data['end_date'] = month_end(serializer.validated_data['end_date'])
        super().perform_create(serializer)
        attempt = serializer.instance
        run_sushi_fetch_attempt_task.apply_async(args=(attempt.pk, True), countdown=1)


class SushiFetchAttemptStatsView(APIView):

    attr_to_query_param_map = {
        'report': ('counter_report', 'counter_report__code'),
        'platform': ('credentials__platform', 'credentials__platform__name'),
        'organization': ('credentials__organization', 'credentials__organization__name'),
    }

    modes = {
        'current': '',  # only attempts that match the current version of their credentials
        'success_and_current': '',  # all successful and unsuccessful for current version of creds
        'all': '',  # all attempts
    }
    default_mode = 'current'

    key_to_attr_map = {value[1]: key for key, value in attr_to_query_param_map.items()}
    key_to_attr_map.update(
        {value[0]: key + '_id' for key, value in attr_to_query_param_map.items()}
    )
    success_metrics = ['download_success', 'processing_success', 'contains_data', 'is_processed']

    def get(self, request):
        organizations = request.user.accessible_organizations()
        filter_params = []
        if 'organization' in request.query_params:
            filter_params.append(
                Q(
                    credentials__organization=get_object_or_404(
                        organizations, pk=request.query_params['organization']
                    )
                )
            )
        else:
            filter_params.append(Q(credentials__organization__in=organizations))
        if 'platform' in request.query_params:
            filter_params.append(Q(credentials__platform_id=request.query_params['platform']))
        if 'date_from' in request.query_params:
            date_from = dateparser.parse(request.query_params['date_from'])
            if date_from:
                filter_params.append(Q(timestamp__date__gte=date_from))
        if 'counter_version' in request.query_params:
            counter_version = request.query_params['counter_version']
            filter_params.append(Q(credentials__counter_version=counter_version))
        # what should be in the result?
        x = request.query_params.get('x', 'report')
        y = request.query_params.get('y', 'platform')
        # what attr on sushi attempt defines success
        success_metric = request.query_params.get('success_metric', self.success_metrics[-1])
        if success_metric not in self.success_metrics:
            success_metric = self.success_metrics[-1]
        # deal with mode - we need to add extra filters for some of the modes
        mode = request.query_params.get('mode', self.default_mode)
        if mode not in self.modes:
            mode = self.default_mode
        if mode == 'all':
            # there is nothing to do here
            pass
        elif mode == 'current':
            filter_params.append(Q(credentials_version_hash=F('credentials__version_hash')))
        elif mode == 'success_and_current':
            # all successful + other that match current version of credentials
            filter_params.append(
                Q(**{success_metric: True})
                | Q(credentials_version_hash=F('credentials__version_hash'))
            )
        # fetch the data - we have different code in presence and absence of date in the data
        if x != 'month' and y != 'month':
            data = self.get_data_no_months(x, y, filter_params, success_metric)
        else:
            dim = x if y == 'month' else y
            data = self.get_data_with_months(dim, filter_params, success_metric)
        # rename the fields back to what was asked for
        out = []
        for obj in data:
            out.append({self.key_to_attr_map.get(key, key): value for key, value in obj.items()})
        return Response(out)

    def get_data_no_months(self, x, y, filter_params: [], success_metric):
        if x not in self.attr_to_query_param_map:
            return HttpResponseBadRequest('unsupported x dimension: "{}"'.format(x))
        if y not in self.attr_to_query_param_map:
            return HttpResponseBadRequest('unsupported y dimension: "{}"'.format(y))
        # we use 2 separate fields for both x and y in order to preserve both the ID of the
        # related field and its text value
        values = []
        values.extend(self.attr_to_query_param_map[x])
        values.extend(self.attr_to_query_param_map[y])
        # now get the output
        qs = (
            SushiFetchAttempt.objects.filter(*filter_params)
            .values(*values)
            .annotate(
                success_count=Count('pk', filter=Q(**{success_metric: True})),
                failure_count=Count('pk', filter=Q(**{success_metric: False})),
            )
        )
        return qs

    def get_data_with_months(self, dim, filter_params: [], success_metric):
        if dim not in self.attr_to_query_param_map:
            return HttpResponseBadRequest('unsupported dimension: "{}"'.format(dim))
        # we use 2 separate fields for dim in order to preserve both the ID of the
        # related field and its text value
        values = self.attr_to_query_param_map[dim]
        months = SushiFetchAttempt.objects.aggregate(start=Min('start_date'), end=Max('end_date'))
        start = month_start(months['start'])
        end = month_end(months['end'])
        cur_date = start
        output = []
        while cur_date < end:
            # now get the output
            for rec in (
                SushiFetchAttempt.objects.filter(*filter_params)
                .filter(start_date__lte=cur_date, end_date__gte=cur_date)
                .values(*values)
                .annotate(
                    success_count=Count('pk', filter=Q(**{success_metric: True})),
                    failure_count=Count('pk', filter=Q(**{success_metric: False})),
                )
            ):
                cur_date_str = '-'.join(str(cur_date).split('-')[:2])
                rec['month'] = cur_date_str[2:]
                rec['month_id'] = cur_date_str
                output.append(rec)
            cur_date = month_start(cur_date + timedelta(days=32))
        return output


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
