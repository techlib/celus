from typing import Optional

from django.db import models
from django.db.models import Sum
from django.http import Http404
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from logs.logic.remap import remap_dicts
from logs.models import AccessLog, ReportType, Dimension
from logs.serializers import DimensionSerializer


class Counter5DataView(APIView):

    implicit_dims = ['date', 'platform', 'metric', 'organization', 'target']

    def _translate_dimension_spec(self, dim_name: str, report_type: ReportType) -> \
            (str, Optional[Dimension]):
        """
        Translate the value which is used to specify the dimension in request to the actual
        dimension for querying
        :param dim_name:
        :return: name of dimension attr on AccessLog model, Dimension instance if not implicit
        """
        if dim_name is None:
            return None, None
        if dim_name in self.implicit_dims:
            return dim_name, None
        if not dim_name.isdigit():
            raise Http404(f'Unknown dimension specifier: {dim_name}')
        dim_idx = int(dim_name)
        dimensions = report_type.dimensions_sorted
        if dim_idx > len(dimensions):
            raise Http404(f'Report type has only {len(dimensions)}, number {dim_idx} was '
                          f'requested')
        return f'dim{dim_idx}', dimensions[dim_idx-1]

    def get(self, request, report_name=None):
        report_type = get_object_or_404(ReportType, short_name=report_name)
        secondary_dim = request.GET.get('sec_dim')
        primary_dim = request.GET.get('prim_dim', 'date')
        # decode the dimensions to find out what we need to have in the query
        prim_dim_name, prim_dim_obj = self._translate_dimension_spec(primary_dim, report_type)
        sec_dim_name, sec_dim_obj = self._translate_dimension_spec(secondary_dim, report_type)

        query_params = {}
        for dim_name in self.implicit_dims:
            value = request.GET.get(dim_name)
            if value:
                field = AccessLog._meta.get_field(dim_name)
                if isinstance(field, models.ForeignKey):
                    query_params[dim_name] = get_object_or_404(field.related_model, pk=value)
        query = AccessLog.objects.filter(**query_params)

        # get the data - we need two separate queries for 1d and 2d cases
        if sec_dim_name:
            data = query.values(prim_dim_name, sec_dim_name).annotate(count=Sum('value')).\
                values(prim_dim_name, 'count', sec_dim_name).order_by(prim_dim_name, sec_dim_name)
        else:
            data = query.values(prim_dim_name).annotate(count=Sum('value')).\
                values(prim_dim_name, 'count').order_by(prim_dim_name)
        # remap the values if text dimensions are involved
        if prim_dim_obj and prim_dim_obj.type == Dimension.TYPE_TEXT:
            remap_dicts(prim_dim_obj, data, prim_dim_name)
        if sec_dim_obj and sec_dim_obj.type == Dimension.TYPE_TEXT:
            remap_dicts(sec_dim_obj, data, sec_dim_name)
        # prepare the data to return
        reply = {'data': data}
        if prim_dim_obj:
            reply[prim_dim_name] = DimensionSerializer(prim_dim_obj).data
        if sec_dim_obj:
            reply[sec_dim_name] = DimensionSerializer(sec_dim_obj).data
        return Response(reply)
