from collections import Counter
from functools import reduce
from pprint import pprint
from time import monotonic

from charts.models import ReportDataView
from core.exceptions import BadRequestException
from core.filters import PkMultiValueFilterBackend
from core.logic.dates import date_filter_from_params, parse_month
from core.logic.serialization import parse_b64json
from core.logic.type_conversion import to_bool
from core.models import REL_ORG_ADMIN, DataSource
from core.permissions import (
    CanAccessOrganizationFromGETAttrs,
    CanAccessOrganizationRelatedObjectPermission,
    CanPostOrganizationDataPermission,
    ManualDataUploadEnabledPermission,
    OrganizationRequiredInDataForNonSuperusers,
    OwnerLevelBasedPermissions,
    SuperuserOrAdminPermission,
    SuperuserOrMasterUserPermission,
)
from core.prometheus import report_access_time_summary, report_access_total_counter
from core.validators import month_validator, pk_list_validator
from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Exists, F, OuterRef, Prefetch, Q, prefetch_related_objects
from django.db.transaction import atomic
from django.http import JsonResponse
from django.urls import reverse
from django.views import View
from logs.logic.export import CSVExport
from logs.logic.queries import StatsComputer, extract_accesslog_attr_query_params
from logs.models import (
    AccessLog,
    Dimension,
    DimensionText,
    FlexibleReport,
    ImportBatch,
    InterestGroup,
    ManualDataUpload,
    ManualDataUploadImportBatch,
    MduState,
    Metric,
    ReportInterestMetric,
    ReportType,
)
from logs.serializers import (
    AccessLogSerializer,
    DimensionSerializer,
    DimensionTextSerializer,
    FlexibleReportSerializer,
    ImportBatchSerializer,
    ImportBatchVerboseSerializer,
    InterestGroupSerializer,
    ManualDataUploadSerializer,
    ManualDataUploadUpdateSerializer,
    ManualDataUploadVerboseSerializer,
    MetricSerializer,
    ReportTypeInterestSerializer,
    ReportTypeSerializer,
)
from organizations.logic.queries import organization_filter_from_org_id
from organizations.models import Organization
from pandas import DataFrame
from publications.models import Platform, Title
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.fields import BooleanField, CharField, ListField
from rest_framework.generics import ListAPIView, get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import DateField, IntegerField, PrimaryKeyRelatedField, Serializer
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_pandas.views import PandasViewBase
from scheduler.models import FetchIntention
from sushi.models import SushiCredentials, SushiFetchAttempt
from tags.models import Tag

from . import filters
from .filters import DimensionFilter, PrimaryDimensionFlexiReportFilter
from .logic.data_coverage import DataCoverageExtractor
from .logic.reporting.slicer import FlexibleDataSlicer, SlicerConfigError, SlicerConfigErrorCode
from .tasks import export_raw_data_task


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 5000


class Counter5DataView(APIView):

    # permission_classes = [IsAuthenticated &
    #                       (SuperuserOrAdminPermission | CanAccessOrganizationFromGETAttrs)
    #                      ]

    def get(self, request, report_type_id):
        report_type = get_object_or_404(ReportType, pk=report_type_id)
        computer = StatsComputer(report_type, request.GET)
        start = monotonic()
        # special attribute signaling that this view is used on dashboard and thus we
        # want to cache the data for extra speed using recache
        dashboard_view = 'dashboard' in request.GET
        data = computer.get_data(request.user, recache=dashboard_view)
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
    queryset = ReportType.objects.filter(materialization_spec__isnull=True)
    filter_backends = [PkMultiValueFilterBackend]

    def get_queryset(self):
        if 'nonzero-only' in self.request.query_params:
            return self.queryset.filter(
                Q(Exists(ImportBatch.objects.filter(report_type_id=OuterRef('pk'))))
                | Q(short_name='interest')
            ).prefetch_related('controlled_metrics')
        return self.queryset.prefetch_related('controlled_metrics')


class MetricViewSet(ReadOnlyModelViewSet):

    serializer_class = MetricSerializer
    queryset = Metric.objects.all()
    filter_backends = [PkMultiValueFilterBackend]


class ReportInterestMetricViewSet(ReadOnlyModelViewSet):
    serializer_class = ReportTypeInterestSerializer
    queryset = (
        ReportType.objects.filter(materialization_spec__isnull=True)
        .exclude(short_name='interest')
        .annotate(used_by_platforms=Count('platforminterestreport__platform', distinct=True))
        .prefetch_related(
            "interest_metrics",
            Prefetch(
                "reportinterestmetric_set",
                queryset=ReportInterestMetric.objects.select_related(
                    "metric", "target_metric", "interest_group"
                ),
            ),
            "controlled_metrics",
        )
    )


class DimensionTextViewSet(ReadOnlyModelViewSet):

    serializer_class = DimensionTextSerializer
    queryset = DimensionText.objects.all()
    pagination_class = StandardResultsSetPagination
    filter_backends = [PkMultiValueFilterBackend, DimensionFilter]

    @property
    def paginator(self):
        if 'pks' in self.request.query_params:
            # if 'pks' are explicitly given, do not paginate and return all
            return None
        return super().paginator

    def post(self, request):
        """
        To get around possible limits in query string length, we also provide a POST interface
        for getting data for a list of IDs.
        It only works if 'pks' attribute is given and does not use pagination
        """
        pks = request.data.get('pks', [])
        dts = DimensionText.objects.filter(pk__in=pks)
        # we do not paginate when using post
        return Response(self.get_serializer(dts, many=True).data)


class AccessLogListViewBase(ListAPIView):

    serializer_class = AccessLogSerializer
    implicit_dims = ['platform', 'metric', 'organization', 'target', 'report_type', 'import_batch']
    pagination_class = StandardResultsSetPagination

    def get_base_queryset(self):
        query_params = self.extract_query_filter_params(self.request)
        return AccessLog.objects.filter(**query_params)

    def get_queryset(self):
        qs = self.get_base_queryset()
        order_args = self.extract_order_args(self.request)
        return qs.order_by(*order_args)

    def paginate_queryset(self, queryset):
        if res := super().paginate_queryset(queryset):
            return self.post_process_data(res)
        return []

    def post_process_data(self, data) -> [AccessLog]:
        text_id_to_text = {}
        tr_to_dimensions = {}
        seen_dims = set()
        # testing showed that prefetching the implicit dimensions here is faster than
        # using `select_related` on the whole queryset before. (roughly 2x faster for 3M rows)
        # It is also slightly faster than using `select_related` here together with `pk__in` filter
        # on the page, even though it does slightly more queries.
        prefetch_related_objects(data, *self.implicit_dims)
        for al in data:
            al.mapped_dim_values_ = {}
            if (dimensions := tr_to_dimensions.get(al.report_type_id)) is None:
                rt = ReportType.objects.get(pk=al.report_type_id)
                dimensions = rt.dimensions_sorted
                tr_to_dimensions[rt.pk] = dimensions
            for i, dim in enumerate(dimensions):
                value = getattr(al, f'dim{i+1}')
                if dim.pk not in seen_dims:
                    # we need to fetch the mappings for this dimension
                    text_id_to_text.update(
                        {
                            dt['id']: dt['text']
                            for dt in DimensionText.objects.filter(dimension=dim).values(
                                'id', 'text'
                            )
                        }
                    )
                    seen_dims.add(dim.pk)
                al.mapped_dim_values_[dim.short_name] = text_id_to_text.get(value, value)
            if al.target:
                al.mapped_dim_values_['isbn'] = al.target.isbn
                al.mapped_dim_values_['issn'] = al.target.issn
                al.mapped_dim_values_['eissn'] = al.target.eissn
        return data

    @classmethod
    def extract_query_filter_params(cls, request) -> dict:
        query_params = date_filter_from_params(request.GET)
        query_params.update(
            extract_accesslog_attr_query_params(
                request.GET, dimensions=cls.implicit_dims, mdu_filter=True
            )
        )
        if 'import_batch' in query_params:
            # add also a filter for report type so that only records with
            # rt matching the import batches rt are shown - no interest, no materialized
            query_params['report_type_id'] = F('import_batch__report_type_id')
        return query_params

    @classmethod
    def extract_order_args(cls, request) -> dict:
        order_by = request.query_params.get('order_by', 'pk')
        desc = to_bool(request.query_params.get('desc', 'false').lower())
        spec = ('-' if desc else '') + order_by
        out = [spec]
        # we need to mix in the pk to make sure the order is deterministic
        # otherwise pagination might not work as expected
        if order_by != 'pk':
            out.append('pk')
        return out


class MduAccessLogListView(AccessLogListViewBase):
    def get_base_queryset(self):
        mdu_id = self.kwargs['mdu_id']
        mdu = get_object_or_404(ManualDataUpload.objects.all(), pk=mdu_id)
        user = self.request.user
        # if the MDU has organization, the user must have access to that organization,
        # if the MDU does not have organization, the user must have access to all organizations
        # because we do not permit access to such MDUs without it (the number of orgs is unclear)
        if mdu.organization_id:
            if not user.accessible_organizations().filter(pk=mdu.organization_id).exists():
                raise NotFound()
        else:
            if not user.is_superuser and not user.is_user_of_master_organization:
                raise NotFound()
        # short-circuit if the mdu is not yet processed
        if not mdu.state == MduState.IMPORTED:
            return AccessLog.objects.none()
        # we help the query planner by adding filters for the platform and report type
        # together with the mdu filter - it makes the query much faster
        # also, by filtering the report type, we remove logs for interest and materialized reports
        # Using the `import_batch_id__in` instead of 'import_batch__mdu = mdu' is a little faster
        # because it skips some table joins
        query_params = {
            'import_batch_id__in': ImportBatch.objects.filter(mdu=mdu)
            .values_list('pk', flat=True)
            .distinct(),
            'platform_id': mdu.platform_id,
            'report_type_id': mdu.report_type_id,
        }
        # if organization is present, we add it to the filter as well
        if mdu.organization_id:
            query_params['organization_id'] = mdu.organization_id
        else:
            query_params['organization_id__in'] = set(
                mdu.import_batches.values_list('organization_id', flat=True)
            )
        return AccessLog.objects.filter(**query_params)


class ImportBatchAccessLogListView(AccessLogListViewBase):
    def get_base_queryset(self):
        ib_id = self.kwargs['ib_id']
        ib = get_object_or_404(
            ImportBatch.objects.filter(
                organization__in=self.request.user.accessible_organizations()
            ),
            pk=ib_id,
        )
        # we help the query planner by adding filters for the platform, report type and org
        # together with the ib filter - it makes the query much faster
        # also, by filtering the report type, we remove logs for interest and materialized reports
        query_params = {
            'import_batch_id': ib_id,
            'platform_id': ib.platform_id,
            'report_type_id': ib.report_type_id,
            'organization': ib.organization,
        }
        return AccessLog.objects.filter(**query_params)


class RawDataExportView(PandasViewBase, AccessLogListViewBase):
    """
    Specialized view for exporting raw data from the access log using pandas.
    It supports several output formats, including CSV, Excel, etc.
    It does not use pagination, but instead returns all data capped at 100k records.
    """

    export_size_limit = 100_000  # limit the number of records in output to this number

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())[: self.export_size_limit]
        queryset = self.post_process_data(queryset)
        serializer = self.get_serializer(queryset, many=True)
        response = Response(serializer.data)
        return self.update_pandas_headers(response)


class RawDataDelayedExportView(APIView):

    permission_classes = [
        IsAuthenticated
        & (
            SuperuserOrAdminPermission
            | SuperuserOrMasterUserPermission
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
    queryset = ImportBatch.objects.all()
    # pagination_class = StandardResultsSetPagination
    filter_backends = [filters.AccessibleFilter, filters.UserFilter, filters.OrderByFilter]

    def get_queryset(self):
        qs = self.queryset
        if 'pk' in self.kwargs:
            # we only add accesslog_count if only one object was requested
            qs = qs.annotate(accesslog_count=Count('accesslog'))
        qs = qs.select_related('organization', 'platform', 'report_type')
        return qs

    def get_serializer_class(self):
        if 'pk' in self.kwargs:
            # for one result, we can use the verbose serializer
            return ImportBatchVerboseSerializer
        return super().get_serializer_class()

    class LookupSerializer(Serializer):
        organization = IntegerField(required=True)
        platform = IntegerField(required=True)
        report_type = IntegerField(required=True)
        months = ListField(child=DateField(), allow_empty=False)

    @action(detail=False, methods=['post'])
    def lookup(self, request):
        """Based on provided list of records
        [("organization", "platform", "report_type", "months")]
        return corresponding import batches
        """
        serializer = self.LookupSerializer(many=True, data=request.data)
        serializer.is_valid(raise_exception=True)

        fltr = Q(pk=None)  # always empty
        for record in serializer.data:
            fltr |= (
                Q(organization_id=record["organization"])
                & Q(platform_id=record["platform"])
                & Q(report_type=record["report_type"])
                & Q(date__in=record["months"])
            )

        qs = ImportBatch.objects.filter(fltr)
        # Only available organizations of the user
        qs = filters.AccessibleFilter().filter_queryset(request, qs, self)
        # Apply ordering
        qs = filters.OrderByFilter().filter_queryset(request, qs, self)
        # Optimizations
        qs = (
            qs.select_related(
                'user',
                'platform',
                'platform__source',
                'organization',
                'report_type',
                'sushifetchattempt',
            )
            .prefetch_related('mdu')
            .annotate(accesslog_count=Count('accesslog'))
        )
        return Response(ImportBatchVerboseSerializer(qs, many=True).data)

    class PurgeSerializer(Serializer):
        batches = ListField(child=IntegerField(), allow_empty=False)

    @atomic
    @action(detail=False, methods=['post'], serializer_class=PurgeSerializer)
    def purge(self, request):
        """Remove all data and related structures of given list of import batches

        Note that if id of given ib doesn't exists it is not treated as an error
        It might have been already deleted
        """
        counter = Counter()
        serializer = self.PurgeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # only accesible batches
        batches = filters.ModifiableFilter().filter_queryset(
            request, ImportBatch.objects.filter(pk__in=serializer.data["batches"]), self
        )

        mdus = list(
            ManualDataUpload.objects.filter(import_batches__in=batches).values_list('pk', flat=True)
        )

        # remove fetch intentions and fetch attempts
        to_delete = (
            FetchIntention.objects.filter(attempt__import_batch__in=batches)
            .values('credentials__pk', 'counter_report__pk', 'start_date')
            .distinct()
        )
        to_delete = [Q(**e) for e in to_delete]
        to_delete = reduce(lambda x, y: x | y, to_delete, Q())
        if to_delete:
            fis_to_delete = FetchIntention.objects.filter(to_delete)
            counter.update(
                SushiFetchAttempt.objects.filter(fetchintention__in=fis_to_delete).delete()[1]
            )

            counter.update(fis_to_delete.delete()[1])

        # remove import batches
        counter.update(batches.delete()[1])

        # remove empty manual data uploads
        counter.update(
            ManualDataUpload.objects.filter(pk__in=mdus, import_batches__isnull=True).delete()[1]
        )

        return Response(counter)

    class DataPresenceParamSerializer(Serializer):

        start_date = CharField(validators=[month_validator], required=True)
        end_date = CharField(validators=[month_validator], required=True)
        credentials = CharField(validators=[pk_list_validator], required=True)

    @action(detail=False, methods=['get'], url_name='data-presence', url_path='data-presence')
    def data_presence(self, request):
        """
        Return a list of combinations of report_type, platform, organization and month for which
        there are some data.

        It requires a filter composed of `start_date`, `end_date` and `credentials` which is a
        comma separated list of credentials primary keys.

        The result is a list of dicts with `report_type_id`, `platform_id`, `organization_id`,
        `date` and `source`. `source` is either `sushi` for data comming from SUSHI or `manual`
        for manually uploaded data.

        Please note that the resulting list may contain data which do not belong to any of the
        credentials provided in `credentials` filter. This is because manually uploaded data
        do not have a direct link to credentials and it would be too costly to remove this extra
        data.
        """
        param_serializer = self.DataPresenceParamSerializer(data=request.GET)
        param_serializer.is_valid(raise_exception=True)
        params = param_serializer.validated_data

        # prepare data from SUSHI - we use fetch attempts for that
        credentials_ids = [int(cid) for cid in params['credentials'].split(',')]
        credentials = SushiCredentials.objects.filter(
            pk__in=credentials_ids, organization__in=request.user.accessible_organizations()
        )

        # decompose credentials to (platform, organization, report_type) tripplets
        pors = []
        for creds in credentials.prefetch_related('counter_reports'):
            for cr in creds.counter_reports.all():
                pors.append((creds.platform_id, creds.organization_id, cr.report_type_id))

        # filter import batches
        qs_args = reduce(
            lambda x, y: (Q(platform_id=y[0]) & Q(organization_id=y[1]) & Q(report_type_id=y[2]))
            | x,
            pors,
            Q(),
        )

        batches = (
            ImportBatch.objects.filter(
                date__gte=parse_month(params['start_date']),
                date__lte=parse_month(params['end_date']),
            )
            .filter(qs_args)
            .annotate(
                has_fa=Exists(SushiFetchAttempt.objects.filter(import_batch_id=OuterRef('pk'))),
                has_mdu=Exists(
                    ManualDataUploadImportBatch.objects.filter(import_batch_id=OuterRef('pk'))
                ),
            )
        )

        return Response(
            {
                'report_type_id': e.report_type_id,
                'platform_id': e.platform_id,
                'organization_id': e.organization_id,
                'date': e.date,
                'source': 'sushi' if e.has_fa else ('manual' if e.has_mdu else 'unknown'),
            }
            for e in batches
        )

    class DataCoverageParamSerializer(Serializer):

        report_type = PrimaryKeyRelatedField(queryset=ReportType.objects.all(), required=False)
        report_view = PrimaryKeyRelatedField(queryset=ReportDataView.objects.all(), required=False)
        start_date = CharField(validators=[month_validator], required=False)
        end_date = CharField(validators=[month_validator], required=False)
        organization = PrimaryKeyRelatedField(queryset=Organization.objects.all(), required=False)
        platform = PrimaryKeyRelatedField(queryset=Platform.objects.all(), required=False)
        title = PrimaryKeyRelatedField(queryset=Title.objects.all(), required=False)
        split_by_org = BooleanField(default=False)
        split_by_platform = BooleanField(default=False)

        def validate(self, data):
            data = super().validate(data)
            if not data.get('report_type') and not data.get('report_view'):
                raise ValidationError('One of "report_type", "report_view" must be present')
            if not data.get('report_type') and not data.get('report_view'):
                raise ValidationError('"report_type" and "report_view" must not be present at once')
            return data

    @action(detail=False, methods=['get'], url_name='data-coverage', url_path='data-coverage')
    def data_coverage(self, request):
        """
        For each month in the date range specified by `start_date` and `end_date` params,
        return how many potential import batches there could be and how many really are,
        thus creating some kind of score of data coverage for each month.
        """
        param_serializer = self.DataCoverageParamSerializer(data=request.GET)
        param_serializer.is_valid(raise_exception=True)
        params = param_serializer.validated_data
        if not (rt := params.get('report_type')):
            rv = params.get('report_view')
            rt = rv.base_report_type

        # disable coverage for selected report types
        if rt.short_name in settings.REPORT_TYPES_WITHOUT_COVERAGE:
            return Response([])

        start_month = parse_month(params.get('start_date'))
        end_month = parse_month(params.get('end_date'))

        extractor = DataCoverageExtractor(
            rt,
            platform=params.get('platform'),
            organization=params.get('organization'),
            title=params.get('title'),
            split_by_org=bool(params.get('split_by_org')),
            split_by_platform=bool(params.get('split_by_platform')),
            start_month=start_month,
            end_month=end_month,
        )
        data = extractor.get_coverage_data()
        return Response(v for k, v in sorted(data.items()))


class ManualDataUploadViewSet(ModelViewSet):

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

    extra_actions_permission_classes = [
        IsAuthenticated
        & ManualDataUploadEnabledPermission
        & (
            (SuperuserOrAdminPermission & OwnerLevelBasedPermissions)
            | (
                OwnerLevelBasedPermissions
                & CanPostOrganizationDataPermission
                & CanAccessOrganizationRelatedObjectPermission
            )
        )
    ]

    def get_serializer_class(self):
        if self.action in ["update", "partial_update"]:
            return ManualDataUploadUpdateSerializer
        else:
            return ManualDataUploadSerializer

    @action(methods=['POST'], detail=True, url_path='preflight')
    def preflight(self, request, pk):
        """triggers preflight computation"""
        mdu = get_object_or_404(ManualDataUpload.objects.all(), pk=pk)

        if mdu.state == MduState.INITIAL:
            # already should be already planned
            # just start it in celery right now
            mdu.plan_preflight()
            return Response({"msg": "generating preflight"})

        elif mdu.state in (MduState.PREFLIGHT, MduState.PREFAILED):
            # regenerate preflight
            if mdu.regenerate_preflight():
                return Response({"msg": "regenerating preflight"})
            else:
                return Response(
                    {"error": "preflight-trigger-failed"}, status=status.HTTP_400_BAD_REQUEST
                )

        return Response(
            {"error": "can-generate-preflight", "state": mdu.state},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @atomic
    @action(methods=['POST'], detail=True, url_path='import-data')
    def import_data(self, request, pk):
        mdu = get_object_or_404(ManualDataUpload.objects.all(), pk=pk)

        if mdu.state == MduState.IMPORTED:
            stats = {
                'existing logs': AccessLog.objects.filter(
                    import_batch_id__in=mdu.import_batches.all()
                ).count()
            }
            return Response(
                {
                    'stats': stats,
                    'import_batches': ImportBatchSerializer(
                        mdu.import_batches.all(), many=True
                    ).data,
                }
            )
        elif (
            mdu.multiple_organizations
            and not request.user.is_superuser
            and not request.user.is_admin_of_master_organization
        ):
            return Response({"error": "not-allowed"}, status.HTTP_403_FORBIDDEN)
        elif mdu.multiple_organizations and mdu.wrong_organizations():
            return Response(
                {"error": "wrong-organization", "organizations": mdu.wrong_organizations()},
                status=status.HTTP_400_BAD_REQUEST,
            )

        elif mdu.clashing_months:
            if clashing_ibs := mdu.clashing_batches():
                clashing = ImportBatchVerboseSerializer(clashing_ibs, many=True).data
                return Response(
                    {"error": "data-conflict", "clashing_import_batches": clashing},
                    status=status.HTTP_409_CONFLICT,
                )
        elif mdu.state == MduState.IMPORTING:
            return Response({"msg": "already importing"})
        elif mdu.can_import(request.user):

            # Set organization to None if organization is read from data
            if mdu.multiple_organizations:
                mdu.organization = None
                mdu.save()

            mdu.plan_import(request.user)
            return Response({"msg": "import started"})

        return Response({"error": "can-not-import"}, status=status.HTTP_400_BAD_REQUEST)

    def get_permissions(self):
        if self.action in {_action.__name__ for _action in self.get_extra_actions()}:
            return [permission() for permission in self.extra_actions_permission_classes]
        else:
            return super().get_permissions()


class OrganizationManualDataUploadViewSet(ReadOnlyModelViewSet):
    """
    This version of the ManualDataUploadViewSet is filtered by organization and offers
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
        qs = (
            ManualDataUpload.objects.filter(**org_filter)
            .select_related('organization', 'platform', 'report_type', 'user')
            .prefetch_related('import_batches', 'import_batches__user')
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


class FlexibleSlicerBaseView(APIView):
    def create_slicer(self, request):
        try:
            slicer = FlexibleDataSlicer.create_from_params(request.query_params)
            slicer.use_clickhouse = request.USE_CLICKHOUSE
            if slicer.tag_roll_up:
                slicer.tag_filter = Q(pk__in=Tag.objects.user_accessible_tags(request.user))
            slicer.add_extra_organization_filter(request.user.accessible_organizations())
            if settings.DEBUG:
                pprint(slicer.config())
            slicer.check_params()
            return slicer
        except SlicerConfigError as e:
            raise BadRequestException(
                {'error': {'message': str(e), 'code': e.code, 'details': e.details}}
            )


class FlexibleSlicerView(FlexibleSlicerBaseView):
    def get(self, request):
        slicer = self.create_slicer(request)
        try:
            part = request.query_params.get('part') if slicer.split_by else None
            if part:
                part = parse_b64json(part)
            data = slicer.get_data(part=part, lang=request.user.language)
        except SlicerConfigError as e:
            return Response(
                {'error': {'message': str(e), 'code': e.code, 'details': e.details}},
                status=HTTP_400_BAD_REQUEST,
            )
        pagination = StandardResultsSetPagination()
        page = pagination.paginate_queryset(data, request)
        return pagination.get_paginated_response(page)


class FlexibleSlicerRemainderView(FlexibleSlicerBaseView):
    def get(self, request):
        slicer = self.create_slicer(request)
        try:
            part = request.query_params.get('part') if slicer.split_by else None
            if part:
                part = parse_b64json(part)
            data = slicer.get_remainder(part=part)
            return Response(data)
        except SlicerConfigError as e:
            return Response(
                {'error': {'message': str(e), 'code': e.code, 'details': e.details}},
                status=HTTP_400_BAD_REQUEST,
            )


class FlexibleSlicerPossibleValuesView(FlexibleSlicerBaseView):
    def get(self, request):
        dimension = request.query_params.get('dimension')
        if not dimension:
            return Response(
                {
                    'error': {
                        'message': 'the "dimension" param is required',
                        'code': SlicerConfigErrorCode.E105,
                    }
                },
                status=HTTP_400_BAD_REQUEST,
            )
        slicer = self.create_slicer(request)
        q = request.query_params.get('q')
        pks = None
        pks_value = request.query_params.get('pks')
        if pks_value:
            try:
                pks = list(map(int, pks_value.split(',')))
            except ValueError as e:
                return Response({'error': {'message': str(e)}})
        return Response(
            slicer.get_possible_dimension_values(
                dimension, ignore_self=True, text_filter=q, pks=pks
            )
        )


class FlexibleSlicerSplitParts(FlexibleSlicerBaseView):

    MAX_COUNT = 1000

    def get(self, request):
        slicer = self.create_slicer(request)
        qs = slicer.get_parts_queryset()
        cropped = False
        count = 0
        if qs:
            count = qs.count()
            if count > self.MAX_COUNT:
                qs = qs[: self.MAX_COUNT]
                cropped = True
        return Response({'count': count, "values": qs or [], "cropped": cropped})


class FlexibleReportViewSet(ModelViewSet):

    queryset = FlexibleReport.objects.none()
    serializer_class = FlexibleReportSerializer
    filter_backends = [PrimaryDimensionFlexiReportFilter]

    def get_queryset(self):
        return FlexibleReport.objects.filter(
            Q(owner=self.request.user)  # owned by user
            | Q(owner__isnull=True, owner_organization__isnull=True)  # completely public
            | Q(
                owner_organization__in=self.request.user.accessible_organizations()
            )  # assigned to owner's organization
        )

    def _preprocess_config(self, request):
        if 'config' not in request.data:
            return None
        slicer = FlexibleDataSlicer.create_from_params(request.data.get('config'))
        return FlexibleReport.serialize_slicer_config(slicer.config())

    def _get_basic_data(self, request):
        owner = request.user.pk if 'owner' not in request.data else request.data.get('owner')
        return {
            'owner': owner,
            'owner_organization': (request.data.get('owner_organization')),
            'name': request.data.get('name'),
        }

    def _check_write_permissions(self, request, owner, owner_organization):
        # only superuser can set other user as owner
        if not (request.user.is_superuser or request.user.is_admin_of_master_organization):
            if owner not in (None, request.user.pk):
                raise PermissionDenied(f'Not allowed to set owner {owner}')
        if owner_organization:
            rel = request.user.organization_relationship(owner_organization)
            if rel < REL_ORG_ADMIN:
                raise PermissionDenied(
                    f'Not allowed to set owner_organization {owner_organization}'
                )
        if not owner and not owner_organization:
            # this should be consortial access level
            if not (request.user.is_superuser or request.user.is_admin_of_master_organization):
                raise PermissionDenied('Not allowed to create consortial level report')

    def create(self, request, *args, **kwargs):
        config = self._preprocess_config(request)
        if config is None:
            return Response(
                {'error': 'Missing "config" parameter for the report'}, status=HTTP_400_BAD_REQUEST
            )
        data = {**self._get_basic_data(request), 'report_config': config}
        self._check_write_permissions(request, data['owner'], data['owner_organization'])
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=HTTP_201_CREATED, headers=headers)

    def _check_update_permissions(self, request, obj: FlexibleReport, delete=False):
        user = request.user

        # generic permission to edit based on current access_level
        if obj.access_level == FlexibleReport.Level.PRIVATE:
            # only owner or superuser may edit
            if not (user == obj.owner or user.is_superuser or user.is_admin_of_master_organization):
                raise PermissionDenied('Not allowed to change private report')
        elif obj.access_level == FlexibleReport.Level.ORGANIZATION:
            # only admin of owner_organization or superuser may edit
            if not (user.is_superuser or user.is_admin_of_master_organization):
                rel = request.user.organization_relationship(obj.owner_organization_id)
                if rel < REL_ORG_ADMIN:
                    raise PermissionDenied('Not allowed to change organization report')
        else:
            # only superuser may edit consortium level reports
            if not (user.is_superuser or user.is_admin_of_master_organization):
                raise PermissionDenied('Not allowed to change consortial report')

        if not delete:
            # now more specific permissions about who can change access level
            # we deduce what the owner and owner_organization would be after the update takes place
            # and check if the current user is allowed to create such a report
            owner = request.data.get('owner') if 'owner' in request.data else obj.owner_id
            owner_organization = (
                request.data.get('owner_organization')
                if 'owner_organization' in request.data
                else obj.owner_organization_id
            )
            self._check_write_permissions(request, owner, owner_organization)

    def update(self, request, *args, **kwargs):
        """
        Permissions for this view should be:

        * private reports (owner != None)
          - only owner may see and change
          - only if the owner is org admin or superuser he may raise the access level to
            organization or consortium

        * organization reports (owner_organization != None)
          - only admin of organization or superuser may change
          - only admin of organization or superuser may change accesslevel

        * consortial reports (owner == None and owner_organization == None)
          - only superuser may change
          - only superuser may change accesslevel
        """
        config = self._preprocess_config(request)
        report = self.get_object()
        self._check_update_permissions(request, report)
        data = {**request.data}
        if config:
            data['report_config'] = config
        serializer = self.get_serializer(report, data=data, partial=kwargs.get('partial'))
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=HTTP_200_OK, headers=headers)

    def destroy(self, request, *args, **kwargs):
        self._check_update_permissions(request, self.get_object(), delete=True)
        return super().destroy(request, *args, **kwargs)
