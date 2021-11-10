from django.db.models import Sum
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from rest_framework.fields import CharField, BooleanField, ListField
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView

from api.auth import extract_org_from_request_api_key
from api.permissions import HasOrganizationAPIKey
from core.logic.dates import parse_month
from core.validators import month_validator
from logs.logic.queries import find_best_materialized_view
from logs.models import AccessLog, ReportType, DimensionText
from publications.models import Title
from sushi.models import SushiCredentials, SushiFetchAttempt


class RedocView(TemplateView):
    template_name = "api/redoc.html"


class PlatformReportView(APIView):
    class ParamSerializer(Serializer):

        month = CharField(validators=[month_validator], required=True)
        dims = CharField(required=True, allow_blank=True)

    class OutputSerializer(Serializer):
        records = ListField(default=list)
        status = CharField()
        complete_data = BooleanField(default=False)

    permission_classes = [HasOrganizationAPIKey]

    def get(self, request, platform_id, report_type):
        organization = extract_org_from_request_api_key(self.request)
        if not organization:
            # we should not get here as the permission_classes should take care of it
            # but this is a guard just in case
            return HttpResponseBadRequest(
                'API key authentication not successful - '
                'you may be missing the api key in the Authorization header'
            )
        param_serializer = self.ParamSerializer(data=request.GET)
        param_serializer.is_valid(raise_exception=True)

        rt = get_object_or_404(ReportType.objects.all(), short_name=report_type)
        month_date = parse_month(param_serializer.validated_data['month'])
        # dimensions
        current_dim_names = {dim.short_name for dim in rt.dimensions_sorted}
        req_dims_str = param_serializer.validated_data['dims']
        req_dims = set(req_dims_str.split('|')) if req_dims_str else set()
        if not req_dims.issubset(current_dim_names):
            unknown_dims = "|".join(req_dims - current_dim_names)
            all_dims = '|'.join(current_dim_names)
            return HttpResponseBadRequest(
                f'Unknown dimensions for this report type: {unknown_dims}. '
                f'Valid dimensions are: {all_dims}'
            )
        reported_dims = [
            f'dim{i+1}' for i, dim in enumerate(rt.dimensions_sorted) if dim.short_name in req_dims
        ]
        # possibly replace the report type with a materialized version
        used_rt = find_best_materialized_view(rt, ['target', 'metric', *reported_dims]) or rt
        qs = AccessLog.objects.filter(
            report_type=used_rt, platform_id=platform_id, date=month_date, organization=organization
        )
        data = qs.values('target', 'metric__short_name', *reported_dims).annotate(hits=Sum('value'))
        text_id_to_text = {
            dt['id']: dt['text']
            for dt in DimensionText.objects.filter(dimension__report_types=rt).values('id', 'text')
        }
        out = []
        titles = {
            t.pk: t
            for t in Title.objects.filter(pk__in=qs.values_list('target_id', flat=True).distinct())
        }
        for al in data:
            rec = {'hits': al['hits'], 'metric': al['metric__short_name']}
            for i, dim in enumerate(rt.dimensions_sorted):
                key = f'dim{i + 1}'
                if key in al:
                    value = al[key]
                    rec[dim.short_name] = text_id_to_text.get(value, value)
            title_id = al['target']
            if title_id:
                title = titles[title_id]
                rec['title'] = title.name
                rec['isbn'] = title.isbn
                rec['issn'] = title.issn
                rec['eissn'] = title.eissn
                rec['doi'] = title.doi
            out.append(rec)

        if len(out) == 0:
            # there are no records there, we need to find out why
            try:
                relevant_sushi = SushiCredentials.objects.get(
                    platform_id=platform_id,
                    organization=organization,
                    counter_reports__report_type=rt,
                )
            except SushiCredentials.DoesNotExist:
                return self._get_response(
                    {'status': 'SUSHI credentials not present for this report'}
                )
            # there is some sushi related to this report
            # check if credentials are active
            if not relevant_sushi.enabled:
                return self._get_response(
                    {'status': 'SUSHI credentials are not automatically harvested'}
                )
            elif relevant_sushi.broken:
                return self._get_response({'status': 'SUSHI credentials are incorrect'})
            # check if the report was marked as broken for current credentials
            report_to_credentials = relevant_sushi.counterreportstocredentials_set.get(
                counter_report__report_type=rt
            )
            if report_to_credentials.broken:
                return self._get_response(
                    {'status': 'Report marked as broken for existing credentials'}
                )
            # we have active credentials, let's check the attempts
            fetch_attempts = SushiFetchAttempt.objects.filter(
                credentials=relevant_sushi,
                counter_report__report_type=rt,
                start_date__lte=month_date,
                end_date__gte=month_date,
            ).order_by('-last_updated')
            if not fetch_attempts:
                return self._get_response({'status': 'Data not yet harvested'})
            last: SushiFetchAttempt = fetch_attempts[0]
            if last.queue_id:
                return self._get_response({'status': 'Harvesting ongoing'})
            if last.error_code == '3030':
                return self._get_response(
                    {'records': out, 'complete_data': True, 'status': 'Empty data'}
                )
            return self._get_response({'status': 'Harvesting error'})

        return self._get_response({'records': out, 'status': 'OK', 'complete_data': True})

    def _get_response(self, data):
        output_serializer = self.OutputSerializer(data=data)
        output_serializer.is_valid(raise_exception=True)
        return Response(output_serializer.data)
