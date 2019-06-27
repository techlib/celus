from django.db.models import Sum
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response

from logs.logic.remap import remap_dicts
from logs.models import Metric, AccessLog, ReportType, Dimension
from logs.serializers import MetricSerializer, DimensionSerializer
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
        primary_dim = request.GET.get('prim_dim', 'date')
        query = AccessLog.objects.filter(
            organization=organization,
            platform=platform,
            metric=metric,
        )
        prim_dim_obj = None
        if primary_dim != 'date':
            prim_dim_idx = int(primary_dim)
            prim_dim_obj = report_type.dimensions_sorted[prim_dim_idx-1]
            prim_dim_name = f'dim{prim_dim_idx}'
        else:
            prim_dim_name = primary_dim

        if secondary_dim:
            dim_idx = int(secondary_dim)
            dim_obj = report_type.dimensions_sorted[dim_idx-1]
            dim_name = f'dim{dim_idx}'
            data = query.values(prim_dim_name, dim_name).annotate(count=Sum('value')).\
                values(prim_dim_name, 'count', dim_name).order_by(prim_dim_name, dim_name)
            if dim_obj.type == Dimension.TYPE_TEXT:
                remap_dicts(dim_obj, data, dim_name)
        else:
            dim_obj = None
            data = query.values(prim_dim_name).annotate(count=Sum('value')).\
                values(prim_dim_name, 'count').order_by(prim_dim_name)
        if primary_dim != 'date' and prim_dim_obj.type == Dimension.TYPE_TEXT:
            remap_dicts(prim_dim_obj, data, prim_dim_name)
        reply = {
            'data': data,
            'organization': OrganizationSerializer(organization).data,
            'metric': MetricSerializer(metric).data,
            'platform': PlatformSerializer(platform).data,
            'sec_dim': DimensionSerializer(dim_obj).data if secondary_dim else None,
            'prim_dim': DimensionSerializer(prim_dim_obj).data if prim_dim_obj else primary_dim,
        }
        return Response(reply)
