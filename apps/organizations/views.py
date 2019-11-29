from collections import Counter

from django.db.models import Count, Q, Sum, Max, Min
from django.db.models.functions import Coalesce
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from core.logic.dates import date_filter_from_params, month_end
from core.permissions import SuperuserOrAdminPermission
from logs.models import ReportType, AccessLog
from organizations.logic.queries import organization_filter_from_org_id
from organizations.tasks import erms_sync_organizations_task
from publications.models import Title
from sushi.models import SushiCredentials
from .serializers import OrganizationSerializer


class OrganizationViewSet(ReadOnlyModelViewSet):

    serializer_class = OrganizationSerializer
    histogram_bins = [(0, 0), (1, 1), (2, 5), (6, 10), (11, 20), (21, 50), (51, 100),
                      (101, 200), (201, 500), (501, 1000)]

    def get_queryset(self):
        """
        Should return only organizations associated with the current user
        :return:
        """
        return self.request.user.accessible_organizations().annotate(
            is_admin=Count('userorganization',
                           filter=Q(userorganization__is_admin=True,
                                    userorganization__user=self.request.user)),
            is_member=Count('userorganization',
                            filter=Q(userorganization__user=self.request.user))
            ).order_by('name')

    @action(detail=True, url_path='sushi-credentials-versions')
    def sushi_credentials_versions(self, request, pk):
        org_filter = organization_filter_from_org_id(pk, request.user)
        data = SushiCredentials.objects.filter(**org_filter).annotate(count=Count('pk')).\
            values('platform', 'counter_version', 'outside_consortium', 'count').\
            filter(count__gt=0).distinct()
        result = {}
        for rec in data:
            if rec['platform'] not in result:
                result[rec['platform']] = []
            result[rec['platform']].append({
                'version': rec['counter_version'],
                'outside_consortium': rec['outside_consortium']
            })
        for key, value in result.items():
            value.sort(key=lambda x: x['version'])
        return Response(result)

    @action(detail=True, url_path='year-interest')
    def year_interest(self, request, pk):
        org_filter = organization_filter_from_org_id(pk, request.user)
        interest_rt = ReportType.objects.get(short_name='interest', source__isnull=True)
        result = []
        for rec in AccessLog.objects \
                .filter(report_type=interest_rt, **org_filter) \
                .values('date__year').distinct() \
                .annotate(interest_sum=Sum('value'))\
                .order_by('date__year'):
            # this is here purely to facilitate renaming of the keys
            result.append({'year': rec['date__year'], 'interest': rec['interest_sum']})
        return Response(result)

    @action(detail=True, url_path='interest')
    def interest(self, request, pk):
        org_filter = organization_filter_from_org_id(pk, request.user)
        date_filter = date_filter_from_params(request.GET)
        interest_rt = ReportType.objects.get(short_name='interest', source__isnull=True)
        data = AccessLog.objects\
            .filter(report_type=interest_rt, **org_filter, **date_filter) \
            .aggregate(interest_sum=Sum('value'), min_date=Min('date'), max_date=Max('date'))
        if data['max_date']:
            # the date might be None and then we do not want to do the math ;)
            data['max_date'] = month_end(data['max_date'])
            data['days'] = (data['max_date'] - data['min_date']).days + 1
        else:
            data['days'] = 0
        return Response(data)

    @action(detail=True, url_path='title-interest-histogram')
    def title_interest_interest(self, request, pk):
        org_filter = organization_filter_from_org_id(pk, request.user)
        date_filter = date_filter_from_params(request.GET)
        interest_rt = ReportType.objects.get(short_name='interest', source__isnull=True)
        counter = Counter()
        query = AccessLog.objects\
            .filter(report_type=interest_rt, **org_filter, **date_filter) \
            .values('target') \
            .annotate(interest_sum=Coalesce(Sum('value'), 0)) \
            .values('interest_sum')
        for rec in query:
            counter[rec['interest_sum']] += 1
        # here we bin it according to self.histogram_bins
        bin_counter = Counter()
        for hits, count in counter.items():
            for start, end in self.histogram_bins:
                if start <= hits <= end:
                    bin_counter[(start, end)] += count
                    break
            else:
                digits = len(str(hits)) - 1
                unit = 10**digits
                start = unit * ((hits-1) // unit)
                end = start + unit
                start += 1
                bin_counter[(start, end)] += count
        # objects to return
        def name(a, b):
            if a == b:
                return str(a)
            return f'{a}-{b}'
        data = [{'count': count, 'start': start, 'end': end, 'name': name(start, end)}
                for (start, end), count in sorted(bin_counter.items())]
        return Response(data)


class StartERMSSyncOrganizationsTask(APIView):

    permission_classes = [SuperuserOrAdminPermission]

    def post(self, request):
        task = erms_sync_organizations_task.delay()
        return Response({
            'id': task.id,
        })
