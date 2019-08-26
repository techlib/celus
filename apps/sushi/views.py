from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from pandas import DataFrame
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from organizations.logic.queries import organization_filter_from_org_id
from organizations.models import Organization
from sushi.models import CounterReportType, SushiFetchAttempt
from sushi.serializers import CounterReportTypeSerializer, SushiFetchAttemptSerializer
from .models import SushiCredentials
from .serializers import SushiCredentialsSerializer


class SushiCredentialsViewSet(ModelViewSet):

    serializer_class = SushiCredentialsSerializer
    queryset = SushiCredentials.objects.none()

    def get_queryset(self):
        user_organizations = self.request.user.accessible_organizations()
        qs = SushiCredentials.objects.filter(organization__in=user_organizations).\
            select_related('organization', 'platform').prefetch_related('active_counter_reports')
        organization_id = self.request.query_params.get('organization')
        if organization_id:
            qs = qs.filter(**organization_filter_from_org_id(organization_id, self.request.user))
        return qs


class CounterReportTypeViewSet(ReadOnlyModelViewSet):

    serializer_class = CounterReportTypeSerializer
    queryset = CounterReportType.objects.all()


class SushiFetchAttemptViewSet(ReadOnlyModelViewSet):

    serializer_class = SushiFetchAttemptSerializer
    queryset = SushiFetchAttempt.objects.none()

    def get_queryset(self):
        organizations = self.request.user.accessible_organizations()
        filter_params = {}
        if 'organization' in self.request.query_params:
            filter_params['credentials__organization'] = \
                get_object_or_404(organizations, pk=self.request.query_params['organization'])
        else:
            filter_params['credentials__organization__in'] = organizations
        if 'platform' in self.request.query_params:
            filter_params['credentials__platform_id'] = self.request.query_params['platform']
        return SushiFetchAttempt.objects.filter(**filter_params).select_related('counter_report')


class SushiFetchAttemptStatsView(APIView):

    attr_to_query_param_map = {
        'report': 'counter_report__code',
        'platform': 'credentials__platform__name',
        'organization': 'credentials__organization__name',
    }
    key_to_attr_map = {value: key for key, value in attr_to_query_param_map.items()}

    def get(self, request):
        organizations = request.user.accessible_organizations()
        filter_params = {}
        if 'organization' in request.query_params:
            filter_params['credentials__organization'] = \
                get_object_or_404(organizations, pk=request.query_params['organization'])
        else:
            filter_params['credentials__organization__in'] = organizations
        if 'platform' in request.query_params:
            filter_params['credentials__platform_id'] = request.query_params['platform']
        # what should be in the result?
        x = request.query_params.get('x', 'report')
        y = request.query_params.get('y', 'platform')
        x_remap = self.attr_to_query_param_map.get(x, x)
        y_remap = self.attr_to_query_param_map.get(y, y)
        # now get the output
        qs = SushiFetchAttempt.objects.filter(**filter_params).values(x_remap, y_remap).annotate(
            success_count=Count('pk', filter=Q(success=True)),
            failure_count=Count('pk', filter=Q(success=False)),
        )
        # rename the fields back to what was asked for
        out = []
        for obj in qs:
            out.append({self.key_to_attr_map.get(key, key): value for key, value in obj.items()})
        return Response(out)
        out = DataFrame(out, columns=[x, y, 'success_count', 'failure_count'])
        print(out)
        print(out.pivot(columns=x, index=y))
        return Response(out.pivot(columns=x, index=y))
