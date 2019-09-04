from time import sleep
from typing import Optional

from django.db import models
from django.db.models import Sum, Count
from django.http import Http404, HttpResponseBadRequest
from pandas import DataFrame
from rest_framework.pagination import PageNumberPagination
from rest_pandas import PandasView
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet

from core.logic.dates import date_filter_from_params
from core.models import DataSource
from logs.logic.custom_import import custom_data_import_precheck, custom_data_to_records, \
    custom_import_preflight_check, import_custom_data
from logs.logic.queries import extract_accesslog_attr_query_params, StatsComputer
from logs.logic.remap import remap_dicts
from logs.models import AccessLog, ReportType, Dimension, DimensionText, Metric, ImportBatch, \
    ManualDataUpload, VirtualReportType
from logs.serializers import DimensionSerializer, ReportTypeSerializer, MetricSerializer, \
    AccessLogSerializer, ImportBatchSerializer, ImportBatchVerboseSerializer, \
    ManualDataUploadSerializer
from organizations.models import Organization
from publications.models import Platform


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class Counter5DataView(APIView):

    def get(self, request, report_type_id=None):
        if report_type_id:
            if 'virtual' in request.GET:
                report_type = get_object_or_404(VirtualReportType, pk=report_type_id)
            else:
                report_type = get_object_or_404(ReportType, pk=report_type_id)
        else:
            report_type = None
        # check for interest in query params
        if not report_type and (request.GET.get('prim_dim') == 'interest' or
                                request.GET.get('sec_dim') == 'interest'):
            # we are dealing with interest based view
            if 'platform' not in request.GET:
                return HttpResponseBadRequest('cannot use interest dimension without specifying '
                                              'platform - interest is platform specific')
            platform = get_object_or_404(Platform.objects.all(), pk=request.GET['platform'])
            data = []
            found_something = False
            for report_type in platform.interest_reports.all():
                computer = StatsComputer()
                data += computer.get_data(report_type, request.GET, request.user)
                found_something = True
            if not found_something:
                # use a default set of reports
                for report_type in ReportType.objects.filter(short_name__in=['TR', 'DR', 'JR1',
                                                                             'DB1']):
                    computer = StatsComputer()
                    data += computer.get_data(report_type, request.GET, request.user)
        else:
            computer = StatsComputer()
            data = computer.get_data(report_type, request.GET, request.user)
        data_format = request.GET.get('format')
        if data_format in ('csv', 'xlsx'):
            # for the bare result, we do not add any extra information, just output the list
            data = DataFrame(data)
            new_keys = [computer.io_prim_dim_name]
            if computer.io_sec_dim_name:
                new_keys.append(computer.io_sec_dim_name)
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
        if computer.prim_dim_obj:
            reply[computer.prim_dim_name] = DimensionSerializer(computer.prim_dim_obj).data
        if computer.sec_dim_obj:
            reply[computer.sec_dim_name] = DimensionSerializer(computer.sec_dim_obj).data
        return Response(reply)


class ReportTypeViewSet(ReadOnlyModelViewSet):

    serializer_class = ReportTypeSerializer
    queryset = ReportType.objects.all()


class MetricViewSet(ReadOnlyModelViewSet):

    serializer_class = MetricSerializer
    queryset = Metric.objects.all()


class RawDataExportView(PandasView):

    serializer_class = AccessLogSerializer
    implicit_dims = ['platform', 'metric', 'organization', 'target', 'report_type', 'import_batch']
    export_size_limit = 50000  # limit the number of records in output to this number

    def get_queryset(self):
        query_params = self.extract_query_filter_params(self.request)
        data = AccessLog.objects.filter(**query_params)\
            .select_related(*self.implicit_dims)[:self.export_size_limit]
        text_id_to_text = {dt['id']: dt['text']
                           for dt in DimensionText.objects.all().values('id', 'text')}
        tr_to_dimensions = {rt.pk: rt.dimensions_sorted for rt in ReportType.objects.all()}
        for al in data:
            al.mapped_dim_values_ = {}
            for i, dim in enumerate(tr_to_dimensions[al.report_type_id]):
                value = getattr(al, f'dim{i+1}')
                if dim.type == dim.TYPE_TEXT:
                    al.mapped_dim_values_[dim.short_name] = text_id_to_text.get(value, value)
                else:
                    al.mapped_dim_values_[dim.short_name] = value
        return data

    @classmethod
    def extract_query_filter_params(cls, request) -> dict:
        query_params = date_filter_from_params(request.GET)
        query_params.update(
            extract_accesslog_attr_query_params(request.GET, dimensions=cls.implicit_dims))
        return query_params


class ImportBatchViewSet(ReadOnlyModelViewSet):

    serializer_class = ImportBatchSerializer
    queryset = ImportBatch.objects.none()
    # pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        if self.request.user.is_from_master_organization:
            qs = ImportBatch.objects.all()
        else:
            qs = ImportBatch.objects.filter(user=self.request.user)
        # make it possible to limit result to only specific user
        if 'user' in self.request.GET:
            qs = qs.filter(user_id=self.request.GET['user'])
        if 'pk' in self.kwargs:
            # we only add accesslog_count if only one object was requested
            qs = qs.annotate(accesslog_count=Count('accesslog'))
        qs = qs.select_related('organization', 'platform', 'report_type')
        order_by = self.request.GET.get('order_by', 'created')
        if self.request.GET.get('desc') in ('true', 1):
            order_by = '-' + order_by
        # ensure that .created is always part of ordering because it is the only value we can
        # be reasonably sure is different between instances
        if order_by != 'created':
            order_by = [order_by, 'created']
        else:
            order_by = [order_by]
        return qs.order_by(*order_by)

    def get_serializer_class(self):
        if 'pk' in self.kwargs:
            # for one result, we can use the verbose serializer
            return ImportBatchVerboseSerializer
        return super().get_serializer_class()


class ManualDataUploadViewSet(ModelViewSet):

    serializer_class = ManualDataUploadSerializer
    queryset = ManualDataUpload.objects.all()


class ManualDataUploadPreflightCheckView(APIView):

    def get(self, request, pk):
        mdu = get_object_or_404(ManualDataUpload.objects.all(), pk=pk)
        stats = custom_import_preflight_check(mdu)
        return Response(stats)


class ManualDataUploadProcessView(APIView):

    def post(self, request, pk):
        mdu = get_object_or_404(ManualDataUpload.objects.all(), pk=pk)  # type: ManualDataUpload
        if mdu.is_processed or mdu.import_batch:
            stats = {'existing logs': mdu.import_batch.accesslog_count}
        else:
            stats = import_custom_data(mdu, request.user)
        return Response({
            'stats': stats,
            'import_batch': ImportBatchSerializer(mdu.import_batch).data
        })


class CustomDimensionsViewSet(ModelViewSet):

    queryset = Dimension.objects.all().order_by('pk')
    serializer_class = DimensionSerializer

    def get_queryset(self):
        organization = get_object_or_404(self.request.user.accessible_organizations(),
                                         pk=self.kwargs.get('organization_pk'))
        try:
            source = organization.private_data_source
        except DataSource.DoesNotExist:
            return Dimension.objects.filter(source__isnull=True)
        return source.dimension_set.all().order_by('pk') | \
            Dimension.objects.filter(source__isnull=True)


class OrganizationReportTypesViewSet(ModelViewSet):

    queryset = ReportType.objects.all()
    serializer_class = ReportTypeSerializer

    def get_queryset(self):
        organization = get_object_or_404(self.request.user.accessible_organizations(),
                                         pk=self.kwargs.get('organization_pk'))
        try:
            source = organization.private_data_source
        except DataSource.DoesNotExist:
            return ReportType.objects.filter(source__isnull=True)
        return source.reporttype_set.all() | ReportType.objects.filter(source__isnull=True)
