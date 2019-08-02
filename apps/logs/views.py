from typing import Optional

from django.db import models
from django.db.models import Sum
from django.http import Http404
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from core.logic.dates import date_filter_from_params
from logs.logic.remap import remap_dicts
from logs.models import AccessLog, ReportType, Dimension, DimensionText, Metric
from logs.serializers import DimensionSerializer, ReportTypeSerializer, MetricSerializer


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
        dimensions = report_type.dimensions_sorted
        for dim_idx, dimension in enumerate(dimensions):
            if dimension.short_name == dim_name:
                break
        else:
            raise Http404(f'Unknown dimension: {dim_name} for report type: {report_type}')
        return f'dim{dim_idx+1}', dimensions[dim_idx]

    def get(self, request, report_name=None):
        """

        :type request: object
        """
        report_type = get_object_or_404(ReportType, short_name=report_name)
        secondary_dim = request.GET.get('sec_dim')
        primary_dim = request.GET.get('prim_dim', 'date')
        # decode the dimensions to find out what we need to have in the query
        prim_dim_name, prim_dim_obj = self._translate_dimension_spec(primary_dim, report_type)
        sec_dim_name, sec_dim_obj = self._translate_dimension_spec(secondary_dim, report_type)
        # construct the query
        query_params = {'report_type': report_type}
        # go over implicit dimensions and add them to the query if GET params are given for this
        for dim_name in self.implicit_dims:
            value = request.GET.get(dim_name)
            if value:
                field = AccessLog._meta.get_field(dim_name)
                if isinstance(field, models.ForeignKey):
                    query_params[dim_name] = get_object_or_404(field.related_model, pk=value)
                else:
                    query_params[dim_name] = value
        # now go over the extra dimensions and add them to filter if requested
        dim_raw_name_to_name = {}
        for i, dim in enumerate(report_type.dimensions_sorted):
            dim_raw_name = 'dim{}'.format(i + 1)
            dim_name = dim.short_name
            dim_raw_name_to_name[dim_raw_name] = dim_name
            value = request.GET.get(dim_name)
            if value:
                if dim.type == dim.TYPE_TEXT:
                    try:
                        value = DimensionText.objects.get(text=value).pk
                    except DimensionText.DoesNotExist:
                        pass  # we leave the value as it is - it will probably lead to empty result
                query_params[dim_raw_name] = value
        # add filter for dates
        query_params.update(date_filter_from_params(request.GET))
        # create the base query
        query = AccessLog.objects.filter(**query_params)
        # get the data - we need two separate queries for 1d and 2d cases
        if sec_dim_name:
            data = query.values(prim_dim_name, sec_dim_name).annotate(count=Sum('value')).\
                values(prim_dim_name, 'count', sec_dim_name).order_by(prim_dim_name, sec_dim_name)
        else:
            data = query.values(prim_dim_name).annotate(count=Sum('value')).\
                values(prim_dim_name, 'count').order_by(prim_dim_name)
        # clean names of organizations
        self.clean_organization_names(request.user, data)
        # remap the values if text dimensions are involved
        if prim_dim_obj and prim_dim_obj.type == Dimension.TYPE_TEXT:
            remap_dicts(prim_dim_obj, data, prim_dim_name)
        elif prim_dim_name in self.implicit_dims:
            # we remap the implicit dims if they are foreign key based
            self.remap_implicit_dim(data, prim_dim_name)
        if sec_dim_obj and sec_dim_obj.type == Dimension.TYPE_TEXT:
            remap_dicts(sec_dim_obj, data, sec_dim_name)
        elif sec_dim_name in self.implicit_dims:
            # we remap the implicit dims if they are foreign key based
            self.remap_implicit_dim(data, sec_dim_name)
        # remap dimension names
        if prim_dim_name in dim_raw_name_to_name:
            new_prim_dim_name = dim_raw_name_to_name[prim_dim_name]
            for rec in data:
                rec[new_prim_dim_name] = rec[prim_dim_name]
                del rec[prim_dim_name]
        if sec_dim_name in dim_raw_name_to_name:
            new_sec_dim_name = dim_raw_name_to_name[sec_dim_name]
            for rec in data:
                rec[new_sec_dim_name] = rec[sec_dim_name]
                del rec[sec_dim_name]
        # prepare the data to return
        reply = {'data': data}
        if prim_dim_obj:
            reply[prim_dim_name] = DimensionSerializer(prim_dim_obj).data
        if sec_dim_obj:
            reply[sec_dim_name] = DimensionSerializer(sec_dim_obj).data
        return Response(reply)

    def remap_implicit_dim(self, data, prim_dim_name):
        """
        Remaps foreign keys to the corresponding values
        :param data: values
        :param prim_dim_name: name of the AccessLog attribute of this dimension
        :return:
        """
        field = AccessLog._meta.get_field(prim_dim_name)
        if isinstance(field, models.ForeignKey):
            mapping = {obj.pk: obj for obj in field.related_model.objects.all()}
            for rec in data:
                if rec[prim_dim_name] in mapping:
                    rec[prim_dim_name] = str(mapping[rec[prim_dim_name]])

    def clean_organization_names(self, user, data):
        """
        If organization is present in the data, we need to anonymize the data for those
        organizations that the user does not have access to.
        :param user: instance of the current user
        :param data: records to be cleaned - organizations should be passed as their primary key
        :return:
        """
        user_organizations = {org.pk for org in user.accessible_organizations()}
        for rec in data:
            if 'organization' in rec and rec['organization'] not in user_organizations:
                rec['organization'] = 'Anonym'


class ReportTypeViewSet(ReadOnlyModelViewSet):

    serializer_class = ReportTypeSerializer
    queryset = ReportType.objects.all()


class MetricViewSet(ReadOnlyModelViewSet):

    serializer_class = MetricSerializer
    queryset = Metric.objects.all()
