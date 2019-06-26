from django.db.models import Sum
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response

from logs.logic.remap import remap_dicts
from logs.models import Metric, AccessLog, ReportType, Dimension
from logs.serializers import MetricSerializer
from organizations.models import Organization
from organizations.serializers import OrganizationSerializer
from publications.models import Platform
from publications.serializers import PlatformSerializer


class Counter5DataView(APIView):

    def get(self, request):
        organization = get_object_or_404(Organization, pk=request.GET.get('organization'))
        metric = get_object_or_404(Metric, pk=request.GET.get('metric'))
        platform = get_object_or_404(Platform, pk=request.GET.get('platform'))
        report_type = get_object_or_404(ReportType, short_name=request.GET.get('report_type'))
        secondary_dim = request.GET.get('sec_dim')
        primary_dim = 'date'
        query = AccessLog.objects.filter(
            source__organization=organization,
            source__platform=platform,
            metric=metric,
        )
        if secondary_dim:
            dim_idx = int(secondary_dim)
            dim_obj = report_type.dimensions_sorted[dim_idx-1]
            print(dim_obj)
            dim_name = f'dim{dim_idx}'
            data = query.values(primary_dim, dim_name).annotate(count=Sum('value')).\
                values(primary_dim, 'count', dim_name).order_by(primary_dim, dim_name)
            if dim_obj.type == Dimension.TYPE_TEXT:
                remap_dicts(dim_obj, data, dim_name)
        else:
            data = query.values(primary_dim).annotate(count=Sum('value')).\
                values(primary_dim, 'count').order_by(primary_dim)
        reply = {
            'data': data,
            'organization': OrganizationSerializer(organization).data,
            'metric': MetricSerializer(metric).data,
            'platform': PlatformSerializer(platform).data,
            'sec_dim': None if not secondary_dim else secondary_dim,
        }
        return Response(reply)
