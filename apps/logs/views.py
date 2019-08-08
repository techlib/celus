from typing import Optional

from django.db import models
from django.db.models import Sum
from django.http import Http404
from django.views import View
from pandas import DataFrame
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
    input_dim_to_query_dim = {'interest': 'metric'}
    extra_query_params = {'interest': {'metric__interest_group__isnull': False}}
    implicit_dim_to_text_fn = {'interest': lambda x: x.name_in_interest_group}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.io_prim_dim_name = None  # name of dimension that was requested and will be outputed
        self.prim_dim_name = None
        self.prim_dim_obj = None
        self.io_sec_dim_name = None  # name of dimension that was requested and will be outputed
        self.sec_dim_name = None
        self.sec_dim_obj = None
        self.dim_raw_name_to_name = {}

    @classmethod
    def _translate_dimension_spec(cls, dim_name: str, report_type: ReportType) -> \
            (str, str, Optional[Dimension]):
        """
        Translate the value which is used to specify the dimension in request to the actual
        dimension for querying
        :param dim_name:
        :return: (output name of the dimension, name of dimension attr on AccessLog model,
                  Dimension instance if not implicit)
        """
        if dim_name is None:
            return None, None, None
        if dim_name in cls.input_dim_to_query_dim:
            return dim_name, cls.input_dim_to_query_dim[dim_name], None
        if dim_name in cls.implicit_dims:
            return dim_name, dim_name, None
        dimensions = report_type.dimensions_sorted
        for dim_idx, dimension in enumerate(dimensions):
            if dimension.short_name == dim_name:
                break
        else:
            raise Http404(f'Unknown dimension: {dim_name} for report type: {report_type}')
        return dimension.short_name, f'dim{dim_idx+1}', dimension

    def _extract_dimension_specs(self, request, report_type):
        """
        Here we get the primary and secondary dimension name and corresponding objects from the
        request based on the report_type
        :param request:
        :param report_type:
        :return:
        """
        secondary_dim = request.GET.get('sec_dim')
        primary_dim = request.GET.get('prim_dim', 'date')
        # decode the dimensions to find out what we need to have in the query
        self.io_prim_dim_name, self.prim_dim_name, self.prim_dim_obj = \
            self._translate_dimension_spec(primary_dim, report_type)
        self.io_sec_dim_name, self.sec_dim_name, self.sec_dim_obj = \
            self._translate_dimension_spec(secondary_dim, report_type)

    def get(self, request, report_name=None):
        data = self.get_data(report_name, request)
        data_format = request.GET.get('format')
        if data_format in ('csv', 'xlsx'):
            # for the bare result, we do not add any extra information, just output the list
            data = DataFrame(data)
            new_keys = [self.io_prim_dim_name]
            if self.io_sec_dim_name:
                new_keys.append(self.io_sec_dim_name)
            # we set the queried dimensions as index so that the default integer index is not
            # added to the result
            data.set_index(new_keys, drop=True, inplace=True)
            return Response(data,
                            headers={
                                'Content-Disposition':
                                    f'attachment; filename="export.{data_format}"'
                            })
        # prepare the data to return
        reply = {'data': data}
        if self.prim_dim_obj:
            reply[self.prim_dim_name] = DimensionSerializer(self.prim_dim_obj).data
        if self.sec_dim_obj:
            reply[self.sec_dim_name] = DimensionSerializer(self.sec_dim_obj).data
        return Response(reply)

    def get_data(self, report_name, request):
        """
        This method encapsulates most of the stuff that is done by this view.
        Based on report_name and the request object, it loads, post-processes, etc. the data
        and returns it
        :param report_name:
        :param request:
        :return:
        """
        if report_name:
            report_type = get_object_or_404(ReportType, short_name=report_name)
        else:
            report_type = None
        self._extract_dimension_specs(request, report_type)
        # construct the query
        query, self.dim_raw_name_to_name = self.construct_query(report_type, request)
        # get the data - we need two separate queries for 1d and 2d cases
        if self.sec_dim_name:
            data = query \
                .values(self.prim_dim_name, self.sec_dim_name) \
                .annotate(count=Sum('value')) \
                .values(self.prim_dim_name, 'count', self.sec_dim_name) \
                .order_by(self.prim_dim_name, self.sec_dim_name)
        else:
            data = query.values(self.prim_dim_name) \
                .annotate(count=Sum('value')) \
                .values(self.prim_dim_name, 'count') \
                .order_by(self.prim_dim_name)
        self.post_process_data(data, request)
        return data

    def post_process_data(self, data, request):
        # clean names of organizations
        self.clean_organization_names(request.user, data)
        # remap the values if text dimensions are involved
        # primary dimension
        if self.prim_dim_obj and self.prim_dim_obj.type == Dimension.TYPE_TEXT:
            remap_dicts(self.prim_dim_obj, data, self.prim_dim_name)
        elif self.prim_dim_name in self.implicit_dims:
            # we remap the implicit dims if they are foreign key based
            to_text_fn = self.implicit_dim_to_text_fn.get(self.io_prim_dim_name, str)
            self.remap_implicit_dim(data, self.prim_dim_name, to_text_fn=to_text_fn)
        # secondary dimension
        if self.sec_dim_obj and self.sec_dim_obj.type == Dimension.TYPE_TEXT:
            remap_dicts(self.sec_dim_obj, data, self.sec_dim_name)
        elif self.sec_dim_name in self.implicit_dims:
            # we remap the implicit dims if they are foreign key based
            to_text_fn = self.implicit_dim_to_text_fn.get(self.io_sec_dim_name, str)
            self.remap_implicit_dim(data, self.sec_dim_name, to_text_fn=to_text_fn)
        # remap dimension names
        if self.prim_dim_name in self.dim_raw_name_to_name:
            new_prim_dim_name = self.dim_raw_name_to_name[self.prim_dim_name]
            for rec in data:
                rec[new_prim_dim_name] = rec[self.prim_dim_name]
                del rec[self.prim_dim_name]
        if self.sec_dim_name in self.dim_raw_name_to_name:
            new_sec_dim_name = self.dim_raw_name_to_name[self.sec_dim_name]
            for rec in data:
                rec[new_sec_dim_name] = rec[self.sec_dim_name]
                del rec[self.sec_dim_name]

    def construct_query(self, report_type, request):
        if report_type:
            query_params = {'report_type': report_type, 'metric__active': True}
        else:
            query_params = {'metric__active': True}
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
        if report_type:
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
        # remap dimension names if the query dim name is different from the i/o one
        if self.prim_dim_name != self.io_prim_dim_name:
            dim_raw_name_to_name[self.prim_dim_name] = self.io_prim_dim_name
        if self.sec_dim_name != self.io_sec_dim_name:
            dim_raw_name_to_name[self.sec_dim_name] = self.io_sec_dim_name
        # add extra filters if requested
        query_params.update(self.extra_query_params.get(self.io_prim_dim_name, {}))
        query_params.update(self.extra_query_params.get(self.io_sec_dim_name, {}))
        # add filter for dates
        query_params.update(date_filter_from_params(request.GET))
        # create the base query
        query = AccessLog.objects.filter(**query_params)
        return query, dim_raw_name_to_name

    @classmethod
    def remap_implicit_dim(cls, data, dim_name, to_text_fn=str):
        """
        Remaps foreign keys to the corresponding values
        :param to_text_fn: function applied to the resolved object to extract text from it
        :param data: values
        :param dim_name: name of the AccessLog attribute of this dimension
        :return:
        """
        field = AccessLog._meta.get_field(dim_name)
        if isinstance(field, models.ForeignKey):
            mapping = {obj.pk: obj for obj in field.related_model.objects.all()}
            for rec in data:
                if rec[dim_name] in mapping:
                    rec[dim_name] = to_text_fn(mapping[rec[dim_name]]).replace('_', ' ')

    @classmethod
    def clean_organization_names(cls, user, data):
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


class RawDataExportView(View):

    pass
