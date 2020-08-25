import traceback
from time import monotonic

from django.core.cache import cache
from django.core.mail import mail_admins
from django.db.models import Count
from django.http import JsonResponse
from django.urls import reverse
from django.views import View
from pandas import DataFrame
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet
from rest_pandas import PandasView

from core.logic.dates import date_filter_from_params
from core.models import DataSource
from core.permissions import (
    OrganizationRequiredInDataForNonSuperusers,
    SuperuserOrAdminPermission,
    OwnerLevelBasedPermissions,
    CanPostOrganizationDataPermission,
    CanAccessOrganizationRelatedObjectPermission,
    CanAccessOrganizationFromGETAttrs,
    ManualDataUploadEnabledPermission,
)
from core.prometheus import report_access_time_summary, report_access_total_counter
from logs.logic.custom_import import custom_import_preflight_check, import_custom_data
from logs.logic.export import CSVExport
from logs.logic.queries import extract_accesslog_attr_query_params, StatsComputer
from logs.models import (
    AccessLog,
    ReportType,
    Dimension,
    DimensionText,
    Metric,
    ImportBatch,
    ManualDataUpload,
    InterestGroup,
)
from logs.serializers import (
    DimensionSerializer,
    ReportTypeSerializer,
    MetricSerializer,
    AccessLogSerializer,
    ImportBatchSerializer,
    ImportBatchVerboseSerializer,
    ManualDataUploadSerializer,
    InterestGroupSerializer,
    ManualDataUploadVerboseSerializer,
)
from organizations.logic.queries import organization_filter_from_org_id
from .tasks import export_raw_data_task


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class Counter5DataView(APIView):

    # permission_classes = [IsAuthenticated &
    #                       (SuperuserOrAdminPermission | CanAccessOrganizationFromGETAttrs)
    #                      ]

    def get(self, request, report_type_id):
        report_type = get_object_or_404(ReportType, pk=report_type_id)
        computer = StatsComputer()
        start = monotonic()
        # special attribute signaling that this view is used on dashboard and thus we
        # want to cache the data for extra speed using recache
        dashboard_view = 'dashboard' in request.GET
        data = computer.get_data(report_type, request.GET, request.user, recache=dashboard_view)
        label_attrs = dict(view_type='chart_data_raw', report_type=computer.used_report_type.pk)
        report_access_total_counter.labels(**label_attrs).inc()
        report_access_time_summary.labels(**label_attrs).observe(monotonic() - start)

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
            return Response(
                data,
                headers={'Content-Disposition': f'attachment; filename="export.{data_format}"'},
            )
        # prepare the data to return
        reply = {'data': data}
        if computer.prim_dim_obj:
            reply[computer.prim_dim_name] = DimensionSerializer(computer.prim_dim_obj).data
        if computer.sec_dim_obj:
            reply[computer.sec_dim_name] = DimensionSerializer(computer.sec_dim_obj).data
        reply['reported_metrics'] = MetricSerializer(
            computer.reported_metrics.values(), many=True
        ).data
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
    export_size_limit = 100_000  # limit the number of records in output to this number

    def get_queryset(self):
        query_params = self.extract_query_filter_params(self.request)
        print('Count:', AccessLog.objects.filter(**query_params).count())
        data = AccessLog.objects.filter(**query_params).select_related(*self.implicit_dims)[
            : self.export_size_limit
        ]
        text_id_to_text = {
            dt['id']: dt['text'] for dt in DimensionText.objects.all().values('id', 'text')
        }
        tr_to_dimensions = {rt.pk: rt.dimensions_sorted for rt in ReportType.objects.all()}
        for al in data:
            al.mapped_dim_values_ = {}
            for i, dim in enumerate(tr_to_dimensions[al.report_type_id]):
                value = getattr(al, f'dim{i+1}')
                if dim.type == dim.TYPE_TEXT:
                    al.mapped_dim_values_[dim.short_name] = text_id_to_text.get(value, value)
                else:
                    al.mapped_dim_values_[dim.short_name] = value
            if al.target:
                al.mapped_dim_values_['isbn'] = al.target.isbn
                al.mapped_dim_values_['issn'] = al.target.issn
                al.mapped_dim_values_['eissn'] = al.target.eissn
        return data

    @classmethod
    def extract_query_filter_params(cls, request) -> dict:
        query_params = date_filter_from_params(request.GET)
        query_params.update(
            extract_accesslog_attr_query_params(request.GET, dimensions=cls.implicit_dims)
        )
        return query_params


class RawDataDelayedExportView(APIView):

    permission_classes = [
        IsAuthenticated
        & (
            SuperuserOrAdminPermission
            | (OrganizationRequiredInDataForNonSuperusers & CanAccessOrganizationFromGETAttrs)
        )
    ]

    def get(self, request):
        query_params = self.extract_query_filter_params(request)
        exporter = CSVExport(query_params)
        return JsonResponse({'total_count': exporter.record_count})

    def post(self, request):
        query_params = self.extract_query_filter_params(request)
        exporter = CSVExport(query_params, zip_compress=True)
        export_raw_data_task.delay(
            query_params, exporter.filename_base, zip_compress=exporter.zip_compress
        )
        return JsonResponse(
            {
                'progress_url': reverse('raw_data_export_progress', args=(exporter.filename_base,)),
                'result_url': exporter.file_url,
            }
        )

    @classmethod
    def extract_query_filter_params(cls, request) -> dict:
        # we use celery with the params, so we need to make it serialization friendly
        # thus we convert the params accordingly using str_date and used_ids
        query_params = date_filter_from_params(request.GET, str_date=True)
        query_params.update(
            extract_accesslog_attr_query_params(
                request.GET, dimensions=CSVExport.implicit_dims, use_ids=True
            )
        )
        return query_params


class RawDataDelayedExportProgressView(View):
    def get(self, request, handle):
        count = None
        if handle and handle.startswith('raw-data-'):
            count = cache.get(handle)
        return JsonResponse({'count': count})


class ImportBatchViewSet(ReadOnlyModelViewSet):

    serializer_class = ImportBatchSerializer
    queryset = ImportBatch.objects.none()
    # pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        if self.request.user.is_from_master_organization:
            qs = ImportBatch.objects.all()
        else:
            qs = ImportBatch.objects.filter(
                organization__in=self.request.user.accessible_organizations()
            )
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
    permission_classes = [
        IsAuthenticated
        & ManualDataUploadEnabledPermission
        & (
            (SuperuserOrAdminPermission & OwnerLevelBasedPermissions)
            | (
                OwnerLevelBasedPermissions
                & CanPostOrganizationDataPermission
                & CanAccessOrganizationRelatedObjectPermission
                & OrganizationRequiredInDataForNonSuperusers
            )
        )
    ]

    @action(methods=['GET'], detail=True, url_path='preflight')
    def preflight_check(self, request, pk):
        mdu = get_object_or_404(ManualDataUpload.objects.all(), pk=pk)
        try:
            stats = custom_import_preflight_check(mdu)
            return Response(stats)
        except Exception as e:
            body = f'URL: {request.path}\n\nException: {e}\n\nTraceback: {traceback.format_exc()}'
            mail_admins('MDU preflight check error', body)
            return Response({'error': str(e)}, status=400)

    @action(methods=['POST'], detail=True, url_path='process')
    def process(self, request, pk):
        mdu = get_object_or_404(ManualDataUpload.objects.all(), pk=pk)  # type: ManualDataUpload
        if mdu.is_processed or mdu.import_batch:
            stats = {'existing logs': mdu.import_batch.accesslog_count}
        else:
            stats = import_custom_data(mdu, request.user)
        return Response(
            {'stats': stats, 'import_batch': ImportBatchSerializer(mdu.import_batch).data}
        )


class OrganizationManualDataUploadViewSet(ReadOnlyModelViewSet):
    """
    This version of the ManualDataUploadViewSet is fitered by organization and offerest
    a verbose output but is read-only. For a less verbose, read-write access, there
    is the 'manual-data-upload' api view that is directly in the API root.
    """

    serializer_class = ManualDataUploadVerboseSerializer
    queryset = ManualDataUpload.objects.all()
    permission_classes = [
        IsAuthenticated
        & ManualDataUploadEnabledPermission
        & (
            (SuperuserOrAdminPermission & OwnerLevelBasedPermissions)
            | (OwnerLevelBasedPermissions & CanAccessOrganizationRelatedObjectPermission)
        )
    ]

    def get_queryset(self):
        org_filter = organization_filter_from_org_id(
            self.kwargs.get('organization_pk'), self.request.user
        )
        qs = ManualDataUpload.objects.filter(**org_filter).select_related(
            'import_batch', 'import_batch__user', 'organization', 'platform', 'report_type', 'user'
        )
        # add access level stuff
        org_to_level = {}  # this is used to cache user access level for the same organization
        for mdu in qs:  # type: SushiCredentials
            if mdu.organization_id not in org_to_level:
                org_to_level[mdu.organization_id] = self.request.user.organization_relationship(
                    mdu.organization_id
                )
            user_org_level = org_to_level[mdu.organization_id]
            mdu.can_edit = user_org_level >= mdu.owner_level
        return qs


class CustomDimensionsViewSet(ModelViewSet):

    queryset = Dimension.objects.all().order_by('pk')
    serializer_class = DimensionSerializer

    def get_queryset(self):
        organization = get_object_or_404(
            self.request.user.accessible_organizations(), pk=self.kwargs.get('organization_pk')
        )
        try:
            source = organization.private_data_source
        except DataSource.DoesNotExist:
            return Dimension.objects.filter(source__isnull=True)
        return source.dimension_set.all().order_by('pk') | Dimension.objects.filter(
            source__isnull=True
        )


class OrganizationReportTypesViewSet(ModelViewSet):

    queryset = ReportType.objects.all()
    serializer_class = ReportTypeSerializer

    def get_queryset(self):
        organization = get_object_or_404(
            self.request.user.accessible_organizations(), pk=self.kwargs.get('organization_pk')
        )
        try:
            source = organization.private_data_source
        except DataSource.DoesNotExist:
            return ReportType.objects.filter(source__isnull=True)
        return source.reporttype_set.all() | ReportType.objects.filter(source__isnull=True)


class InterestGroupViewSet(ReadOnlyModelViewSet):

    queryset = InterestGroup.objects.all()
    serializer_class = InterestGroupSerializer
