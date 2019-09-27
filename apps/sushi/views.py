from datetime import timedelta
from time import sleep

import dateparser
from django.db.models import Count, Q, Max, Min
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from pandas import DataFrame
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from core.logic.dates import month_start, month_end
from organizations.logic.queries import organization_filter_from_org_id
from organizations.models import Organization
from sushi.models import CounterReportType, SushiFetchAttempt
from sushi.serializers import CounterReportTypeSerializer, SushiFetchAttemptSerializer
from sushi.tasks import run_sushi_fetch_attempt_task
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


class SushiFetchAttemptViewSet(ModelViewSet):

    serializer_class = SushiFetchAttemptSerializer
    queryset = SushiFetchAttempt.objects.none()
    http_method_names = ['get', 'post', 'options', 'head']

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
        return SushiFetchAttempt.objects.filter(**filter_params).\
            select_related('counter_report', 'credentials__organization')

    def perform_create(self, serializer: SushiFetchAttemptSerializer):
        serializer.validated_data['in_progress'] = True
        serializer.validated_data['end_date'] = month_end(serializer.validated_data['end_date'])
        super().perform_create(serializer)
        attempt = serializer.instance
        run_sushi_fetch_attempt_task.apply_async(args=(attempt.pk,), countdown=1)


class SushiFetchAttemptStatsView(APIView):

    attr_to_query_param_map = {
        'report': ('counter_report', 'counter_report__code'),
        'platform': ('credentials__platform', 'credentials__platform__name'),
        'organization': ('credentials__organization', 'credentials__organization__name'),
    }

    key_to_attr_map = {value[1]: key for key, value in attr_to_query_param_map.items()}
    key_to_attr_map.update({value[0]: key+'_id' for key, value in attr_to_query_param_map.items()})
    success_metrics = ['download_success', 'processing_success', 'contains_data']

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
        if 'date_from' in request.query_params:
            date_from = dateparser.parse(request.query_params['date_from'])
            if date_from:
                filter_params['timestamp__date__gte'] = date_from
        if 'counter_version' in request.query_params:
            counter_version = request.query_params['counter_version']
            filter_params['credentials__counter_version'] = counter_version
        # what should be in the result?
        x = request.query_params.get('x', 'report')
        y = request.query_params.get('y', 'platform')
        # what attr on sushi attempt defines success
        success_metric = request.query_params.get('success_metric', self.success_metrics[-1])
        if success_metric not in self.success_metrics:
            success_metric = self.success_metrics[-1]
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

    def get_data_no_months(self, x, y, filter_params, success_metric):
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
        qs = SushiFetchAttempt.objects.filter(**filter_params).values(*values).annotate(
            success_count=Count('pk', filter=Q(**{success_metric: True})),
            failure_count=Count('pk', filter=Q(**{success_metric: False})),
        )
        return qs

    def get_data_with_months(self, dim, filter_params, success_metric):
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
            for rec in SushiFetchAttempt.objects.filter(**filter_params).\
                filter(start_date__lte=cur_date, end_date__gte=cur_date).values(*values).annotate(
                success_count=Count('pk', filter=Q(**{success_metric: True})),
                failure_count=Count('pk', filter=Q(**{success_metric: False})),
            ):
                cur_date_str = '-'.join(str(cur_date).split('-')[:2])
                rec['month'] = cur_date_str[2:]
                rec['month_id'] = cur_date_str
                output.append(rec)
            cur_date = month_start(cur_date + timedelta(days=32))
        return output
