import json
from collections import Counter

from django.conf import settings
from django.db.models import Count, Q, Sum, Max, Min, F, Exists, OuterRef
from django.db.models.functions import Coalesce
from django.http import HttpResponseBadRequest
from django.utils.text import slugify
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework import status

from core.filters import PkMultiValueFilterBackend
from core.logic.bins import bin_hits
from core.logic.dates import date_filter_from_params, month_end
from core.models import DataSource
from core.permissions import SuperuserOrAdminPermission
from logs.logic.queries import replace_report_type_with_materialized
from logs.models import ReportType, AccessLog, InterestGroup
from organizations.logic.queries import organization_filter_from_org_id
from organizations.tasks import erms_sync_organizations_task
from publications.models import PlatformTitle, Platform
from publications.serializers import PlatformSerializer
from recache.util import recache_queryset
from sushi.models import SushiCredentials
from .models import UserOrganization, Organization
from .serializers import OrganizationSerializer, OrganizationSimpleSerializer


class OrganizationViewSet(ReadOnlyModelViewSet):

    serializer_class = OrganizationSerializer
    histogram_bins = [
        (0, 0),
        (1, 1),
        (2, 5),
        (6, 10),
        (11, 20),
        (21, 50),
        (51, 100),
        (101, 200),
        (201, 500),
        (501, 1000),
    ]
    queryset = Organization.objects.all()
    filter_backends = [PkMultiValueFilterBackend]

    def get_queryset(self):
        """
        Should return only organizations associated with the current user
        :return:
        """
        qs = super().get_queryset()
        qs = qs.filter(pk__in=self.request.user.accessible_organizations())
        return qs.annotate(
            is_admin=Count(
                'userorganization',
                filter=Q(userorganization__is_admin=True, userorganization__user=self.request.user),
            ),
            is_member=Count('userorganization', filter=Q(userorganization__user=self.request.user)),
        ).order_by('name')

    @action(detail=True, url_path='sushi-credentials-versions')
    def sushi_credentials_versions(self, request, pk):
        org_filter = organization_filter_from_org_id(pk, request.user)
        data = (
            SushiCredentials.objects.filter(**org_filter)
            .annotate(count=Count('pk'))
            .values('platform', 'counter_version', 'outside_consortium', 'count')
            .filter(count__gt=0)
            .distinct()
        )
        result = {}
        for rec in data:
            if rec['platform'] not in result:
                result[rec['platform']] = []
            result[rec['platform']].append(
                {'version': rec['counter_version'], 'outside_consortium': rec['outside_consortium']}
            )
        for key, value in result.items():
            value.sort(key=lambda x: x['version'])
        return Response(result)

    @action(detail=True, url_path='year-interest')
    def year_interest(self, request, pk):
        org_filter = organization_filter_from_org_id(pk, request.user)
        interest_rt = ReportType.objects.get(short_name='interest', source__isnull=True)
        result = []
        for rec in (
            AccessLog.objects.filter(report_type=interest_rt, **org_filter)
            .values('date__year')
            .distinct()
            .annotate(interest_sum=Sum('value'))
            .order_by('date__year')
        ):
            # this is here purely to facilitate renaming of the keys
            result.append({'year': rec['date__year'], 'interest': rec['interest_sum']})
        return Response(result)

    @action(detail=True, url_path='interest')
    def interest(self, request, pk):
        org_filter = organization_filter_from_org_id(pk, request.user)
        date_filter = date_filter_from_params(request.GET)
        interest_rt = ReportType.objects.get(short_name='interest', source__isnull=True)
        accesslog_filter_params = {'report_type': interest_rt, **org_filter, **date_filter}
        replace_report_type_with_materialized(accesslog_filter_params)
        # The following is a more natural query for this data, but because aggregate
        # returns a dict in Django, it would not be possible to recache the result
        # (we need a queryset for this).
        #
        # data = AccessLog.objects.filter(**accesslog_filter_params).aggregate(
        #     interest_sum=Sum('value'), min_date=Min('date'), max_date=Max('date')
        # )
        #
        # This is why we use the following hack where the .values call does group by
        # a column that has a NULL value for all records and thus returns the same data
        # as the previous aggregate but in the form of a queryset
        data = recache_queryset(
            AccessLog.objects.filter(**accesslog_filter_params)
            .values('dim7')
            .annotate(interest_sum=Sum('value'), min_date=Min('date'), max_date=Max('date')),
            origin='organization-interest',
        )
        if data:
            data = data[0]
            del data['dim7']  # residue after grouping, not needed
        else:
            data = {}
        if data.get('max_date'):
            # the date might be None and then we do not want to do the math ;)
            data['max_date'] = month_end(data['max_date'])
            data['days'] = (data['max_date'] - data['min_date']).days + 1
        else:
            data['days'] = 0
        return Response(data)

    @action(detail=True, url_path='title-interest-histogram')
    def title_interest_histogram(self, request, pk):
        org_filter = organization_filter_from_org_id(pk, request.user)
        date_filter = date_filter_from_params(request.GET)
        interest_rt = ReportType.objects.get(short_name='interest', source__isnull=True)
        counter = Counter()
        query = (
            AccessLog.objects.filter(report_type=interest_rt, **org_filter, **date_filter)
            .values('target')
            .annotate(interest_sum=Coalesce(Sum('value'), 0))
            .values('interest_sum')
        )
        for rec in query:
            counter[rec['interest_sum']] += 1
        # here we bin it according to self.histogram_bins
        bin_counter = bin_hits(counter, histogram_bins=self.histogram_bins)

        # objects to return
        def name(a, b):
            if a == b:
                return str(a)
            return f'{a}-{b}'

        data = [
            {'count': count, 'start': start, 'end': end, 'name': name(start, end)}
            for (start, end), count in sorted(bin_counter.items())
        ]
        return Response(data)

    @action(detail=False, methods=['post'], url_path='create-user-default')
    def create_user_default(self, request):
        """
        Lets a user create an organization if account creation is allowed and this user does
        not have an organization yet.
        """
        if not settings.ALLOW_USER_REGISTRATION:
            return HttpResponseBadRequest(
                json.dumps({'error': 'Organization creation is not allowed'}),
                content_type='application/json',
            )
        organization_count = request.user.organizations.count()
        if organization_count > 0:
            return HttpResponseBadRequest(
                json.dumps({'error': 'User is allowed to create only one organization'}),
                content_type='application/json',
            )
        serializer = OrganizationSimpleSerializer()
        valid_data = serializer.validate(request.data)
        org = serializer.create(valid_data)
        # update all language mutations
        # so the organization name is properly shown even when langage changes
        org.name_cs = valid_data["name"]
        org.name_en = valid_data["name"]
        data_source = DataSource.objects.create(organization=org, type=DataSource.TYPE_ORGANIZATION)
        # we add the just created data source as source for the organization itself
        # it looks strange, but it is a usable way how to say that this is a user-created
        # organization
        org.source = data_source
        org.internal_id = f"{slugify(request.user.username)}#{ slugify(org.name) }"[:50]
        org.save()
        # associate the user with this organization as admin
        UserOrganization.objects.create(
            user=request.user, organization=org, is_admin=True, source=data_source
        )
        return Response(OrganizationSerializer(org).data, status=status.HTTP_201_CREATED)

    @action(detail=True, url_path='platform-overlap')
    def platform_overlap(self, request, pk):
        """
        API that returns a specific reply for platform-platform overlap analysis
        """
        org_filter = organization_filter_from_org_id(pk, request.user)
        date_filter_params1 = date_filter_from_params(request.GET)
        date_filter_params2 = date_filter_from_params(
            request.GET, key_start='title__platformtitle__'
        )
        query = (
            PlatformTitle.objects.filter(**org_filter, **date_filter_params1)
            .filter(
                title=F("title__platformtitle__title"),
                organization=F("title__platformtitle__organization"),
                **date_filter_params2,
            )
            .values("platform", "title__platformtitle__platform_id")
            .annotate(count=Count("title_id", distinct=True))
        )
        query = recache_queryset(query, origin='overlap-analysis')
        result = [
            {
                'platform1': rec['platform'],
                'platform2': rec['title__platformtitle__platform_id'],
                'overlap': rec['count'],
            }
            for rec in query
        ]
        return Response(result)

    @action(detail=True, url_path='all-platforms-overlap')
    def all_platforms_overlap(self, request, pk):
        """
        API that returns a specific reply for platform overlap with all other platforms
        """
        org_filter = organization_filter_from_org_id(pk, request.user)
        date_filter_params1 = date_filter_from_params(request.GET)
        is_on_other_platform = PlatformTitle.objects.filter(
            title_id=OuterRef('title_id'),
            organization_id=OuterRef('organization_id'),
            **date_filter_params1,
        ).exclude(platform_id=OuterRef('platform_id'))
        query = (
            PlatformTitle.objects.filter(**org_filter, **date_filter_params1)
            .annotate(elsewhere=Exists(is_on_other_platform))
            .values("platform")
            .annotate(count=Count("title_id", filter=Q(elsewhere=True), distinct=True))
        )
        # APO = 'all platform overlap'
        query = recache_queryset(query, origin='APO-titles')

        # interest for the titles
        interest_rt = ReportType.objects.get(short_name='interest', source__isnull=True)
        title_id_filter = {
            'target_id__in': PlatformTitle.objects.filter(**org_filter, **date_filter_params1)
            .filter(Exists(is_on_other_platform))
            .values("title_id")
            .distinct()
        }
        accesslog_filter = {
            'report_type': interest_rt,
            **org_filter,
            **date_filter_params1,
            **title_id_filter,
        }
        replace_report_type_with_materialized(accesslog_filter)
        overlap_interests = (
            AccessLog.objects.filter(**accesslog_filter)
            .values('platform')
            .annotate(interest=Coalesce(Sum('value'), 0))
        )
        overlap_interests = recache_queryset(overlap_interests, origin='APO-interest')
        pk_to_interest = {rec['platform']: rec['interest'] for rec in overlap_interests}

        # overall interest
        accesslog_filter = {
            'report_type': interest_rt,
            **org_filter,
            **date_filter_params1,
        }
        replace_report_type_with_materialized(accesslog_filter)
        total_overlap_interests = (
            AccessLog.objects.filter(**accesslog_filter)
            .values('platform')
            .annotate(interest=Coalesce(Sum('value'), 0))
        )
        total_overlap_interests = recache_queryset(
            total_overlap_interests, origin='APO-total-interest'
        )
        pk_to_total_interest = {rec['platform']: rec['interest'] for rec in total_overlap_interests}

        result = [
            {
                'platform': rec['platform'],
                'overlap': rec['count'],
                'overlap_interest': pk_to_interest.get(rec['platform'], 0),
                'total_interest': pk_to_total_interest.get(rec['platform'], 0),
            }
            for rec in query
        ]
        return Response(result)


class StartERMSSyncOrganizationsTask(APIView):

    permission_classes = [SuperuserOrAdminPermission]

    def post(self, request):
        task = erms_sync_organizations_task.delay()
        return Response({'id': task.id,})
