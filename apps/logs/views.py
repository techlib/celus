import operator
import traceback
from collections import Counter
from datetime import date
from functools import reduce
from logging import getLogger
from pprint import pprint
from typing import Any, Dict, Optional, Tuple

from charts.models import ReportDataView
from core.exceptions import BadRequestException
from core.filters import PkMultiValueFilterBackend
from core.logic.dates import date_filter_from_params, last_month, parse_month
from core.logic.serialization import parse_b64json
from core.logic.type_conversion import to_bool
from core.models import REL_ORG_ADMIN, REL_UNREL_USER, DataSource, User
from core.permissions import (
    CanAccessOrganizationFromGETAttrs,
    CanAccessOrganizationRelatedObjectPermission,
    CanPostOrganizationDataPermission,
    OrganizationRequiredInDataForNonSuperusers,
    OwnerLevelBasedPermissions,
    SuperuserOrAdminPermission,
    SuperuserOrMasterUserPermission,
)
from core.renderers import PandasCSVRenderer, PandasExcelRenderer
from core.serializers import UserSerializerForMailing
from core.tasks import async_mail_admins
from core.validators import month_validator, pk_list_validator
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import BooleanField as DbBooleanField
from django.db.models import (
    Case,
    Count,
    Exists,
    F,
    Max,
    OuterRef,
    Prefetch,
    Q,
    Sum,
    Value,
    When,
    prefetch_related_objects,
)
from django.db.models import IntegerField as DbIntegerField
from django.db.models.functions import Coalesce, Extract
from django.db.transaction import atomic, on_commit
from django.http import JsonResponse, StreamingHttpResponse
from django.urls import reverse
from django.views import View
from hcube.api.models.query import CubeQuery
from organizations.logic.queries import organization_filter_from_org_id
from organizations.models import Organization
from publications.models import Platform, Title
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.fields import (
    BooleanField,
    CharField,
    CurrentUserDefault,
    HiddenField,
    ListField,
)
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListAPIView, get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.serializers import DateField, IntegerField, PrimaryKeyRelatedField, Serializer
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ReadOnlyModelViewSet
from scheduler.models import FetchIntention
from sushi.models import (
    AttemptStatus,
    CounterReportsToCredentials,
    CounterReportType,
    CounterVersionChoices,
    SushiCredentials,
    SushiFetchAttempt,
)
from sushi.serializers import CounterReportTypeSerializer

from config.permissions import IsAuthenticatedWithOptional2FA
from logs.logic.export import CSVExport
from logs.logic.queries import StatsComputer, extract_accesslog_attr_query_params
from logs.models import (
    AccessLog,
    DimensionText,
    FlexibleReport,
    FlexibleReportUserEmail,
    ImportBatch,
    InterestConfig,
    InterestDimensionValueMapping,
    InterestGroup,
    ManualDataUpload,
    ManualDataUploadImportBatch,
    MduState,
    Metric,
    ReportInterestMetric,
    ReportType,
    ReportTypeToDimension,
)
from logs.serializers import (
    AccessLogSerializer,
    DimensionSerializer,
    DimensionTextSerializer,
    FlexibleReportSerializer,
    FlexibleReportUserEmailCreateSerializer,
    FlexibleReportUserEmailSerializer,
    ImportBatchSerializer,
    ImportBatchVerboseSerializer,
    InterestComputationDescriptionSerializer,
    InterestGroupDefinitionsSerializer,
    InterestGroupSerializer,
    ManualDataUploadSerializer,
    ManualDataUploadVerboseSerializer,
    MetricSerializer,
    ReportTypeInterestSerializer,
    ReportTypeSerializer,
)

from . import filters
from .exceptions import MultipleReportTypes, NibblerErrors, UnsupportedReportType, WhitelistingError
from .fields import CommaSeparatedPrimaryKeyRelatedField
from .filters import DimensionFilter, PrimaryDimensionFlexiReportFilter
from .logic.data_coverage import DataCoverageExtractor
from .logic.reporting.helpers import user_visible_tags
from .logic.reporting.slicer import FlexibleDataSlicer, SlicerConfigError, SlicerConfigErrorCode
from .permissions import AccessiblePlatformFromOrganization
from .tasks import (
    export_raw_data_task,
    send_report_mailing_raw_task,
    sync_organizationplatform_records_task,
)

logger = getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 5000


class Counter5DataView(APIView):
    # permission_classes = [IsAuthenticatedWithOptional2FA &
    #                       (SuperuserOrAdminPermission | CanAccessOrganizationFromGETAttrs)
    #                      ]

    renderer_classes = [JSONRenderer, PandasCSVRenderer, PandasExcelRenderer]

    def get(self, request, report_type_id):
        report_type = get_object_or_404(ReportType, pk=report_type_id)
        computer = StatsComputer(report_type, request.GET)
        # special attribute signaling that this view is used on dashboard and thus we
        # want to cache the data for extra speed using recache
        dashboard_view = "dashboard" in request.GET
        data = computer.get_data(request.user, recache=dashboard_view)

        data_format = request.GET.get("format")
        if data_format in ("csv", "xlsx"):
            from pandas import DataFrame  # noqa - slow import

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
                headers={"Content-Disposition": f'attachment; filename="export.{data_format}"'},
            )
        # prepare the data to return
        reply = {"data": data}
        if computer.prim_dim_obj:
            reply[computer.prim_dim_name] = DimensionSerializer(computer.prim_dim_obj).data
        if computer.sec_dim_obj:
            reply[computer.sec_dim_name] = DimensionSerializer(computer.sec_dim_obj).data
        reply["reported_metrics"] = MetricSerializer(
            computer.reported_metrics.values(), many=True
        ).data
        return Response(reply)


class ReportTypeViewSet(ReadOnlyModelViewSet):
    serializer_class = ReportTypeSerializer
    queryset = ReportType.objects.exclude_materialized().select_related(
        "source", "counterreporttype"
    )
    filter_backends = [PkMultiValueFilterBackend]

    def get_queryset(self):
        if "nonzero-only" in self.request.query_params:
            extra_attrs = {}
            if self.request.GET.get("start_date"):
                extra_attrs["date__gte"] = self.request.GET["start_date"]
            if self.request.GET.get("end_date"):
                extra_attrs["date__lte"] = self.request.GET["end_date"]
            return self.queryset.filter(
                Q(Exists(ImportBatch.objects.filter(report_type_id=OuterRef("pk"), **extra_attrs)))
                | Q(short_name="interest")
            ).prefetch_related("controlled_metrics")
        return self.queryset.prefetch_related("controlled_metrics")


class MetricViewSet(ReadOnlyModelViewSet):
    serializer_class = MetricSerializer
    queryset = Metric.objects.all()
    filter_backends = [PkMultiValueFilterBackend]


class ReportInterestMetricViewSet(ReadOnlyModelViewSet):
    serializer_class = ReportTypeInterestSerializer

    def get_queryset(self):
        # Get organization ID from query params if present
        org_filter = organization_filter_from_org_id(
            self.request.query_params.get("organization_id"), self.request.user, clickhouse=True
        )

        # Get the appropriate interest config
        if org_filter:
            try:
                org = Organization.objects.get(pk=org_filter["organization_id"])
                ic = org.get_interest_config()
            except Organization.DoesNotExist:
                ic = InterestConfig.objects.default()
            record_count_annotation = Sum(
                "importbatch__record_count",
                filter=Q(importbatch__organization_id=org_filter["organization_id"]),
            )
        else:
            ic = InterestConfig.objects.default()
            record_count_annotation = Sum("importbatch__record_count")

        return (
            ReportType.objects.exclude_materialized()
            .exclude(short_name="interest", source__isnull=True)
            .annotate(
                is_counter=Exists(CounterReportType.objects.filter(report_type=OuterRef("pk")))
            )
            .annotate(record_count=Coalesce(record_count_annotation, 0))
            .prefetch_related(
                "interest_metrics",
                Prefetch(
                    "reportinterestmetric_set",
                    queryset=ReportInterestMetric.objects.filter(
                        Q(interest_profile=ic.interest_profile) | Q(interest_profile__isnull=True)
                    )
                    .select_related("metric", "interest_group")
                    .prefetch_related("filters", "filters__dimension"),
                ),
            )
        )


class DimensionTextViewSet(ReadOnlyModelViewSet):
    serializer_class = DimensionTextSerializer
    queryset = DimensionText.objects.all()
    pagination_class = StandardResultsSetPagination
    filter_backends = [PkMultiValueFilterBackend, DimensionFilter]

    @property
    def paginator(self):
        if "pks" in self.request.query_params:
            # if 'pks' are explicitly given, do not paginate and return all
            return None
        return super().paginator

    def post(self, request):
        """
        To get around possible limits in query string length, we also provide a POST interface
        for getting data for a list of IDs.
        It only works if 'pks' attribute is given and does not use pagination
        """
        pks = request.data.get("pks", [])
        dts = DimensionText.objects.filter(pk__in=pks)
        # we do not paginate when using post
        return Response(self.get_serializer(dts, many=True).data)


class AccessLogListViewBase(ListAPIView):
    serializer_class = AccessLogSerializer
    implicit_dims = [
        "platform",
        "metric",
        "organization",
        "target",
        "item",
        "report_type",
        "import_batch",
    ]
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
                value = getattr(al, f"dim{i + 1}")
                if dim.pk not in seen_dims:
                    # we need to fetch the mappings for this dimension
                    text_id_to_text.update(
                        {
                            dt["id"]: dt["text"]
                            for dt in DimensionText.objects.filter(dimension=dim).values(
                                "id", "text"
                            )
                        }
                    )
                    seen_dims.add(dim.pk)
                al.mapped_dim_values_[dim.short_name] = text_id_to_text.get(value, value)
            if al.target:
                al.mapped_dim_values_["isbn"] = al.target.isbn
                al.mapped_dim_values_["issn"] = al.target.issn
                al.mapped_dim_values_["eissn"] = al.target.eissn
        return data

    @classmethod
    def extract_query_filter_params(cls, request) -> dict:
        query_params = date_filter_from_params(request.GET)
        query_params.update(
            extract_accesslog_attr_query_params(
                request.GET, dimensions=cls.implicit_dims, mdu_filter=True
            )
        )
        if "import_batch" in query_params:
            # add also a filter for report type so that only records with
            # rt matching the import batches rt are shown - no interest, no materialized
            query_params["report_type_id"] = F("import_batch__report_type_id")
        return query_params

    @classmethod
    def extract_order_args(cls, request) -> list:
        order_by = request.query_params.get("order_by", "pk")
        desc = to_bool(request.query_params.get("desc", "false").lower())
        spec = ("-" if desc else "") + order_by
        out = [spec]
        # we need to mix in the pk to make sure the order is deterministic
        # otherwise pagination might not work as expected
        if order_by != "pk":
            out.append("pk")
        return out


class MduAccessLogViewMixin:
    def get_base_queryset(self):
        mdu_id = self.kwargs["mdu_id"]
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
            "import_batch_id__in": ImportBatch.objects.filter(mdu=mdu)
            .values_list("pk", flat=True)
            .distinct(),
            "platform_id": mdu.platform_id,
            "report_type_id": mdu.report_type_id,
        }
        # if organization is present, we add it to the filter as well
        if mdu.organization_id:
            query_params["organization_id"] = mdu.organization_id
        else:
            query_params["organization_id__in"] = set(
                mdu.import_batches.values_list("organization_id", flat=True)
            )
        return AccessLog.objects.filter(**query_params)


class MduAccessLogListView(MduAccessLogViewMixin, AccessLogListViewBase):
    pass


class ImportBatchAccessLogListView(AccessLogListViewBase):
    def get_base_queryset(self):
        ib_id = self.kwargs["ib_id"]
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
            "import_batch_id": ib_id,
            "platform_id": ib.platform_id,
            "report_type_id": ib.report_type_id,
            "organization": ib.organization,
        }
        return AccessLog.objects.filter(**query_params)


class RawDataDelayedExportView(APIView):
    permission_classes = [
        IsAuthenticatedWithOptional2FA
        & (
            SuperuserOrAdminPermission
            | SuperuserOrMasterUserPermission
            | (OrganizationRequiredInDataForNonSuperusers & CanAccessOrganizationFromGETAttrs)
        )
    ]

    def get(self, request):
        query_params = self.extract_query_filter_params(request)
        exporter = CSVExport(query_params, use_clickhouse=request.USE_CLICKHOUSE)
        return JsonResponse({"total_count": exporter.record_count})

    def post(self, request):
        query_params = self.extract_query_filter_params(request)
        compress = request.GET.get("compress", None) != "false"
        exporter = CSVExport(
            query_params, zip_compress=compress, use_clickhouse=request.USE_CLICKHOUSE
        )
        export_raw_data_task.delay(
            query_params, exporter.filename_base, zip_compress=exporter.zip_compress
        )
        return JsonResponse(
            {
                "progress_url": reverse("raw_data_export_progress", args=(exporter.filename_base,)),
                "result_url": exporter.file_url,
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
        if handle and handle.startswith("raw-data-"):
            count = cache.get(handle)
        return JsonResponse({"count": count})


class CounterExportView(GenericViewSet):
    class CounterReportTypeWithUsedSerializer(CounterReportTypeSerializer):
        used = IntegerField(required=True)

        class Meta(CounterReportTypeSerializer.Meta):
            fields = CounterReportTypeSerializer.Meta.fields + ("used",)

    queryset = CounterReportType.objects.annotate().all()

    serializer_class = CounterReportTypeWithUsedSerializer

    def _extract_dates(self, params) -> (Optional[date], Optional[date]):
        start_date = params.get("start_date")
        start_date = start_date and parse_month(start_date)
        end_date = params.get("end_date")
        end_date = end_date and parse_month(end_date)
        return start_date, end_date

    class CounterDownloadSerializer(Serializer):
        organization = IntegerField(required=True)
        platform = IntegerField(required=True)
        start_date = CharField(validators=[month_validator], required=False)
        end_date = CharField(validators=[month_validator], required=False)

    @action(detail=False, methods=["get"], url_name="used", url_path="used")
    def used(self, request):
        param_serializer = self.CounterDownloadSerializer(data=request.GET)
        param_serializer.is_valid(raise_exception=True)
        params = param_serializer.validated_data
        start_date, end_date = self._extract_dates(params)

        extra_filter = {}
        if start_date:
            extra_filter["report_type__importbatch__date__gte"] = start_date
        if end_date:
            extra_filter["report_type__importbatch__date__lte"] = end_date

        qs = (
            self.get_queryset()
            .filter(counter_version__in=CounterVersionChoices.c5x())
            .annotate(
                used=Count(
                    "report_type__importbatch__pk",
                    distinct=True,
                    filter=Q(
                        report_type__importbatch__organization_id=params["organization"],
                        report_type__importbatch__platform_id=params["platform"],
                        **extra_filter,
                    ),
                )
            )
        )
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=True, methods=["get"], url_name="download", url_path="download")
    def download(self, request, pk):
        param_serializer = self.CounterDownloadSerializer(data=request.GET)
        param_serializer.is_valid(raise_exception=True)
        params = param_serializer.validated_data
        start_date, end_date = self._extract_dates(params)

        organization = get_object_or_404(
            request.user.accessible_organizations(), pk=params["organization"]
        )
        counter_report_type = get_object_or_404(
            CounterReportType.objects.all(), pk=self.kwargs["pk"]
        )
        platform = get_object_or_404(Platform.objects.all(), pk=params["platform"])

        exporter_class = counter_report_type.get_counter_exporter_class()
        if not exporter_class:
            return Response(
                f"Counter exports for '{counter_report_type.code}' are not supported",
                status=status.HTTP_400_BAD_REQUEST,
            )

        exporter = exporter_class(
            organization,
            platform,
            counter_report_type.report_type,
            start_date=start_date,
            end_date=end_date,
        )
        filename = f"{platform.short_name}-{counter_report_type.code}.csv"
        response = StreamingHttpResponse(exporter.csv())
        response["Content-Type"] = "text/csv"
        response["Cache-Control"] = "no-cache"
        response["Content-Disposition"] = f"attachment; filename={filename}"

        return response


class ImportBatchViewSet(ReadOnlyModelViewSet):
    serializer_class = ImportBatchSerializer
    queryset = ImportBatch.objects.all()
    # pagination_class = StandardResultsSetPagination
    filter_backends = [filters.AccessibleFilter, filters.UserFilter, filters.OrderByFilter]

    def get_queryset(self):
        qs = self.queryset
        if "pk" in self.kwargs:
            # we only add accesslog_count if only one object was requested
            qs = qs.annotate(accesslog_count=Count("accesslog"))
        qs = qs.select_related("organization", "platform", "report_type")
        return qs

    def get_serializer_class(self):
        if "pk" in self.kwargs:
            # for one result, we can use the verbose serializer
            return ImportBatchVerboseSerializer
        return super().get_serializer_class()

    class LookupSerializer(Serializer):
        organization = IntegerField(required=True)
        platform = IntegerField(required=True)
        report_type = IntegerField(required=True)
        months = ListField(child=DateField(), allow_empty=False)

    @action(detail=False, methods=["post"])
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
        qs = qs.select_related(
            "user",
            "platform",
            "platform__source",
            "organization",
            "report_type",
            "sushifetchattempt",
        ).prefetch_related("mdu")
        return Response(ImportBatchVerboseSerializer(qs, many=True).data)

    class PurgeSerializer(Serializer):
        batches = ListField(child=IntegerField(), allow_empty=False)

    @atomic
    @action(detail=False, methods=["post"], serializer_class=PurgeSerializer)
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
            ManualDataUpload.objects.filter(import_batches__in=batches).values_list("pk", flat=True)
        )

        # remove fetch intentions and fetch attempts
        to_delete = (
            FetchIntention.objects.filter(attempt__import_batch__in=batches)
            .values("credentials__pk", "counter_report__pk", "start_date")
            .distinct()
        )
        to_delete = [Q(**e) for e in to_delete]
        to_delete = reduce(lambda x, y: x | y, to_delete, Q())

        # remove import batches first
        # otherwise there might be a race condition when deleting
        # credentials or entire platform
        counter.update(batches.delete()[1])

        if to_delete:
            fis_to_delete = FetchIntention.objects.filter(to_delete)
            counter.update(
                SushiFetchAttempt.objects.filter(fetchintention__in=fis_to_delete).delete()[1]
            )

            counter.update(fis_to_delete.delete()[1])

        # remove empty manual data uploads
        counter.update(
            ManualDataUpload.objects.filter(pk__in=mdus, import_batches__isnull=True).delete()[1]
        )

        return Response(counter)

    class DataPresenceParamSerializer(Serializer):
        start_date = CharField(validators=[month_validator], required=True)
        end_date = CharField(validators=[month_validator], required=True)
        credentials = CharField(validators=[pk_list_validator], required=True)

    @action(detail=False, methods=["get"], url_name="data-presence", url_path="data-presence")
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
        credentials_ids = [int(cid) for cid in params["credentials"].split(",")]
        credentials = SushiCredentials.objects.filter(
            pk__in=credentials_ids, organization__in=request.user.accessible_organizations()
        )

        # decompose credentials to (platform, organization, report_type) tripplets
        pors = []
        for creds in credentials.prefetch_related("counter_reports"):
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
                date__gte=parse_month(params["start_date"]),
                date__lte=parse_month(params["end_date"]),
            )
            .filter(qs_args)
            .annotate(
                has_fa=Exists(SushiFetchAttempt.objects.filter(import_batch_id=OuterRef("pk"))),
                has_mdu=Exists(
                    ManualDataUploadImportBatch.objects.filter(import_batch_id=OuterRef("pk"))
                ),
            )
        )

        return Response(
            {
                "report_type_id": e.report_type_id,
                "platform_id": e.platform_id,
                "organization_id": e.organization_id,
                "date": e.date,
                "source": "sushi" if e.has_fa else ("manual" if e.has_mdu else "unknown"),
            }
            for e in batches
        )

    class DataCoverageCoreParamSerializer(Serializer):
        start_date = CharField(validators=[month_validator], required=False)
        end_date = CharField(validators=[month_validator], required=False)
        organization = CommaSeparatedPrimaryKeyRelatedField(
            queryset=Organization.objects.all(), required=False, many=True
        )

    class DataCoverageBasicParamSerializer(DataCoverageCoreParamSerializer):
        report_type = PrimaryKeyRelatedField(queryset=ReportType.objects.all(), required=False)
        report_view = PrimaryKeyRelatedField(queryset=ReportDataView.objects.all(), required=False)
        platform = CommaSeparatedPrimaryKeyRelatedField(
            queryset=Platform.objects.all(), required=False, many=True
        )

        def validate(self, data):
            data = super().validate(data)
            if not data.get("report_type") and not data.get("report_view"):
                raise ValidationError('One of "report_type", "report_view" must be present')
            if data.get("report_type") and data.get("report_view"):
                raise ValidationError('"report_type" and "report_view" must not be present at once')
            return data

    class DataCoverageFullParamSerializer(DataCoverageBasicParamSerializer):
        title = PrimaryKeyRelatedField(queryset=Title.objects.all(), required=False)
        split_by_org = BooleanField(default=False)
        split_by_platform = BooleanField(default=False)
        split_by_date = BooleanField(default=True)

    @classmethod
    def get_params_and_rt(cls, serializer_cls, request) -> Tuple[Dict[str, Any], ReportType]:
        param_serializer = serializer_cls(data=request.GET)
        param_serializer.is_valid(raise_exception=True)
        params = param_serializer.validated_data
        if not (rt := params.get("report_type")):
            rv = params.get("report_view")
            rt = rv.base_report_type
        return params, rt

    @action(detail=False, methods=["get"], url_name="data-coverage", url_path="data-coverage")
    def data_coverage(self, request):
        """
        For each month in the date range specified by `start_date` and `end_date` params,
        return how many potential import batches there could be and how many really are,
        thus creating some kind of score of data coverage for each month.
        """
        params, rt = self.get_params_and_rt(self.DataCoverageFullParamSerializer, request)
        # disable coverage for selected report types
        if rt.short_name in settings.REPORT_TYPES_WITHOUT_COVERAGE:
            return Response([])

        start_month = parse_month(params.get("start_date"))
        end_month = parse_month(params.get("end_date"))

        extractor = DataCoverageExtractor(
            rt,
            platform=params.get("platform"),
            organization=params.get("organization"),
            title=params.get("title"),
            split_by_org=bool(params.get("split_by_org")),
            split_by_platform=bool(params.get("split_by_platform")),
            split_by_date=bool(params.get("split_by_date")),
            start_month=start_month,
            end_month=end_month,
        )
        data = extractor.get_coverage_data()
        return Response(v for k, v in sorted(data.items()))

    @action(
        detail=False,
        methods=["get"],
        url_name="data-coverage-harvestable",
        url_path="data-coverage-harvestable",
    )
    def data_coverage_harvestable(self, request):
        """
        Returns a list of credentials which are verified and do not have 100 % coverage
        in the date range specified by `start_date` and `end_date` params.
        For each credentials ID, it returns a list of months which are not covered.
        """
        params, rt = self.get_params_and_rt(self.DataCoverageBasicParamSerializer, request)
        # disable coverage for selected report types
        if rt.short_name in settings.REPORT_TYPES_WITHOUT_COVERAGE:
            return Response([])

        start_month = parse_month(params.get("start_date"))
        end_month = parse_month(params.get("end_date"))

        # we use the maximum splitting because this would enable us to analyze the data
        # and assign it to individual credentials
        extractor = DataCoverageExtractor(
            rt,
            platform=params.get("platform"),
            organization=params.get("organization"),
            start_month=start_month,
            end_month=end_month,
            split_by_org=True,
            split_by_platform=True,
            split_by_date=True,
        )
        data = extractor.get_coverage_data()
        org_platform_to_month = {}
        for rec in data.values():
            if "ib_max" not in rec:
                # this can only happen if there is a discrepancy between OrganizationPlatform
                # records and actual import batches. This should not happen, but it does sometimes.
                # The only thing we can do is to schedule the cleanup job and skip this record for
                # now. An email will be sent to the admins from the task if anything is fixed.
                sync_organizationplatform_records_task.delay(
                    reason="detected in `data_coverage_harvestable`"
                )
                continue
            if rec["ib_count"] < rec["ib_max"] and rec["verified_credentials"] > 0:
                # data are not complete, but there are some verified credentials
                key = (rec["organization_id"], rec["platform_id"])
                org_platform_to_month.setdefault(key, []).append(rec["date"])
        # we need to get all found combinations of organization and platform into the query
        # for SushiCredentials. In order to make the query slightly simpler then listing all the
        # combinations one by one, we group keys by organization and use __in lookup for each org.
        org_to_platforms = {}
        for org_id, platform_id in org_platform_to_month.keys():
            org_to_platforms.setdefault(org_id, []).append(platform_id)
        out = []
        query_chunks = [
            Q(organization_id=org_id, platform_id__in=platform_ids)
            for org_id, platform_ids in org_to_platforms.items()
        ]
        if query_chunks:
            for cr in (
                SushiCredentials.objects.annotate_verified()
                .filter(
                    reduce(operator.or_, query_chunks),
                    counterreportstocredentials__counter_report__report_type=rt,
                    verified=True,
                    broken__isnull=True,
                    counterreportstocredentials__broken__isnull=True,
                )
                .order_by("organization_id", "platform_id", "-enabled")
                .select_related("organization", "platform")
                .prefetch_related(
                    Prefetch(
                        "counterreportstocredentials_set",
                        queryset=CounterReportsToCredentials.objects.filter(
                            counter_report__report_type=rt
                        ),
                        to_attr="filtered_cr2c",
                    )
                )
                .distinct("organization_id", "platform_id")
            ):
                # the combination of .order_by() and .distinct() above makes sure that
                # for duplicated credentials, the one with enabled=True is first
                # (we only want to use one set of credentials per org/platform otherwise the counts
                #  would be off)
                months = org_platform_to_month.get((cr.organization_id, cr.platform_id), [])

                # Try to limit months by last_harvestable_month
                if last_harvestable_month := cr.last_harvestable_month:
                    months = [m for m in months if m >= last_harvestable_month]

                out.append(
                    {
                        "credentials_id": cr.pk,
                        "org": cr.organization.name,
                        "platform": cr.platform.name,
                        "months": months,
                    }
                )

        return Response(out)

    @action(
        detail=False,
        methods=["get"],
        url_name="total-data-coverage",
        url_path="total-data-coverage",
    )
    def total_data_coverage(self, request):
        """
        Returns an overall data coverage for all report types and all platforms.
        """
        param_serializer = self.DataCoverageCoreParamSerializer(data=request.GET)
        param_serializer.is_valid(raise_exception=True)
        start_month = parse_month(param_serializer.validated_data.get("start_date"))
        end_month = parse_month(param_serializer.validated_data.get("end_date"))
        organization = param_serializer.validated_data.get("organization")

        extra_attrs = {}
        if start_month:
            extra_attrs["date__gte"] = start_month
        if end_month:
            extra_attrs["date__lte"] = end_month
        rt_qs = ReportType.objects.exclude_materialized().filter(
            Q(Exists(ImportBatch.objects.filter(report_type_id=OuterRef("pk"), **extra_attrs)))
        )

        totals = Counter()
        for rt in rt_qs:
            extractor = DataCoverageExtractor(
                rt,
                organization=organization,
                start_month=start_month,
                end_month=end_month,
                split_by_org=False,
                split_by_platform=False,
                split_by_date=False,
            )
            cov_data = extractor.get_coverage_data()
            if cov_data:
                data = cov_data[()]  # empty tuple key because we don't split
                totals["ib_count"] += data["ib_count"]
                totals["ib_max"] += data["ib_max"]

        totals["ratio"] = (totals["ib_count"] / totals["ib_max"]) if totals["ib_max"] else None
        return Response(totals)

    class ImportBatchCreateEmptySerializer(Serializer):
        organization = PrimaryKeyRelatedField(queryset=Organization.objects.all(), required=True)
        report_type = PrimaryKeyRelatedField(queryset=ReportType.objects.all(), required=True)
        platform = PrimaryKeyRelatedField(queryset=Platform.objects.all(), required=True)
        date = DateField(required=True)
        user = HiddenField(default=CurrentUserDefault())

        def validate_date(self, value):
            """
            Date must be in the past, before to the currently harvested month
            """
            currently_harvested_month = last_month()
            if value >= currently_harvested_month:
                raise ValidationError(
                    "Date must be in the past, before the currently harvested month"
                )
            return value

        def validate(self, data):
            """
            Check that there is no matching import batch, but there is a failed fetch attempt.
            """
            if ImportBatch.objects.filter(
                organization=data["organization"],
                report_type=data["report_type"],
                platform=data["platform"],
                date=data["date"],
            ).exists():
                raise ValidationError("Import batch already exists")
            if not SushiFetchAttempt.objects.filter(
                credentials__organization=data["organization"],
                counter_report__report_type=data["report_type"],
                credentials__platform=data["platform"],
                status__in=AttemptStatus.errors(),
                start_date=data["date"],
            ).exists():
                raise ValidationError("No previous failed fetch attempt exists")
            return data

        def save(self, **kwargs):
            return ImportBatch.objects.create(manual_empty=True, **self.validated_data)

    @action(detail=False, methods=["post"], url_name="create-empty", url_path="create-empty")
    def create_empty(self, request):
        """
        Create an empty import batch for given report type, platform and date.
        """
        serializer = self.ImportBatchCreateEmptySerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        # check that user has access to the organization as admin
        if (
            request.user.organization_relationship(serializer.validated_data["organization"].pk)
            < REL_ORG_ADMIN
        ):
            raise PermissionDenied("Not allowed to create import batch for this organization")
        ib = serializer.save()
        return Response(ImportBatchSerializer(ib).data, status=status.HTTP_201_CREATED)


class ManualDataUploadViewSet(
    mixins.CreateModelMixin, mixins.DestroyModelMixin, mixins.RetrieveModelMixin, GenericViewSet
):
    queryset = ManualDataUpload.objects.all()
    permission_classes = [
        IsAuthenticatedWithOptional2FA
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
        IsAuthenticatedWithOptional2FA
        & (
            (SuperuserOrAdminPermission & OwnerLevelBasedPermissions)
            | (
                OwnerLevelBasedPermissions
                & CanPostOrganizationDataPermission
                & CanAccessOrganizationRelatedObjectPermission
            )
        )
        & AccessiblePlatformFromOrganization
    ]

    serializer_class = ManualDataUploadSerializer

    def _action_permission_check(self, pk, request) -> ManualDataUpload:
        # Permissions to get this MDU should be checked in
        # extra_actions_permission_classes, so we don't need to limit query here
        mdu = get_object_or_404(ManualDataUpload.objects.all(), pk=pk)

        # check permission for object MDU
        permissions = self.get_permissions()
        if not all(p.has_object_permission(request, self, mdu) for p in permissions):
            raise PermissionDenied(f"Not allowed change mdu {pk}")

        return mdu

    @atomic
    @action(methods=["POST"], detail=True, url_path="confirm")
    def confirm(self, request, pk):
        """confirms selected report type"""
        mdu = self._action_permission_check(pk, request)

        if mdu.state == MduState.INITIAL:
            mdu.state = MduState.CONFIRMED
            mdu.save()

            # Plan preflight generation
            on_commit(mdu.plan_preflight)

            return Response({"msg": "confirmed"})
        else:
            return Response({"error": "already-confirmed"}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["POST"], detail=True, url_path="preflight")
    def preflight(self, request, pk):
        """triggers preflight computation"""
        mdu = self._action_permission_check(pk, request)

        # Update org
        if org_id := request.data.get("organization_id"):
            if organization := request.user.admin_organizations().filter(pk=org_id).last():
                mdu.organization = organization
            else:
                raise PermissionDenied(f"Not allowed to set organization to {org_id}")
        else:
            mdu.organization = None
        mdu.save()

        if mdu.state == MduState.CONFIRMED:
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
    @action(methods=["POST"], detail=True, url_path="import-data")
    def import_data(self, request, pk):
        mdu = get_object_or_404(ManualDataUpload.objects.all(), pk=pk)

        # check permission for object MDU
        permissions = self.get_permissions()
        if not all(p.has_object_permission(request, self, mdu) for p in permissions):
            raise PermissionDenied(f"Not allowed change mdu {pk}")

        if mdu.state == MduState.IMPORTED:
            stats = {
                "existing logs": AccessLog.objects.filter(
                    import_batch_id__in=mdu.import_batches.all()
                ).count()
            }
            return Response(
                {
                    "stats": stats,
                    "import_batches": ImportBatchSerializer(
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

    def perform_create(self, serializer):
        from celus_nibbler.errors import WrongFileFormatError, XlsError  # noqa - slow import

        try:
            return super().perform_create(serializer)
        except NibblerErrors as e:
            raise BadRequestException({"nibbler_errors": [err.dict() for err in e.errors]}) from e
        except MultipleReportTypes as e:
            raise BadRequestException(
                {"multiple_report_types": [e.id for e in e.report_types]}
            ) from e
        except UnicodeDecodeError as e:
            raise BadRequestException({"encoding_error": str(e)}) from e
        except WrongFileFormatError as e:
            raise BadRequestException({"wrong_file_format": str(e)}) from e
        except XlsError as e:
            raise BadRequestException({"xls_error": str(e)}) from e
        except UnsupportedReportType as e:
            raise BadRequestException({"unsupported_report_type": e.report_type_names}) from e
        except ValidationError as e:
            raise BadRequestException({"non_field_errors": [str(e)]}) from e
        except WhitelistingError as e:
            raise BadRequestException({"whitelisting_error": str(e)}) from e


class OrganizationManualDataUploadViewSet(ReadOnlyModelViewSet):
    """
    This version of the ManualDataUploadViewSet is filtered by organization and offers
    a verbose output but is read-only. For a less verbose, read-write access, there
    is the 'manual-data-upload' api view that is directly in the API root.
    """

    serializer_class = ManualDataUploadVerboseSerializer
    queryset = ManualDataUpload.objects.all()
    permission_classes = [
        IsAuthenticatedWithOptional2FA
        & (
            (SuperuserOrAdminPermission & OwnerLevelBasedPermissions)
            | (OwnerLevelBasedPermissions & CanAccessOrganizationRelatedObjectPermission)
        )
    ]
    pagination_class = StandardResultsSetPagination
    filter_backends = [
        SearchFilter,
        filters.MultiPlatformFilter,
        filters.MultiReportTypeFilter,
        filters.OrderByFilter,
    ]
    search_fields = [
        "platform__name",
        "platform__short_name",
        "organization__name",
        "organization__short_name",
        "report_type__name",
        "report_type__short_name",
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    ]

    def filter_org_qs(self, qs):
        org_filter = organization_filter_from_org_id(
            self.kwargs.get("organization_pk"), self.request.user
        )
        return qs.filter(**org_filter)

    def get_queryset(self):
        qs = self.filter_org_qs(super().get_queryset())
        qs = qs.select_related("organization", "platform", "report_type", "user").prefetch_related(
            "import_batches", "import_batches__user"
        )
        # add access level stuff
        # calculate organization levels
        organization_ids = qs.distinct("organization_id").values_list("organization_id", flat=True)
        levels = {e: self.request.user.organization_relationship(e) for e in organization_ids}

        whens = [When(organization_id=k, then=Value(v)) for k, v in levels.items()]
        qs = qs.annotate(
            user_org_level=Case(*whens, default=REL_UNREL_USER, output_field=DbIntegerField()),
            can_edit=Case(
                When(user_org_level__gte=F("owner_level"), then=Value(True)),
                default=Value(False),
                output_field=DbBooleanField(),
            ),
        )

        return qs

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request, organization_pk):
        qs = self.filter_org_qs(self.queryset)  # unfiltered qs
        counts = {
            "platforms": list(
                qs.order_by("platform_id")
                .values("platform_id")
                .annotate(count=Count("pk"))
                .values("platform_id", "count")
            ),
            "report_types": list(
                qs.order_by("report_type_id")
                .values("report_type_id")
                .annotate(count=Count("pk"))
                .values("report_type_id", "count")
            ),
        }
        return Response({"counts": counts})


class OrganizationReportTypesViewSet(ModelViewSet):
    queryset = ReportType.objects.all()
    serializer_class = ReportTypeSerializer

    def get_queryset(self):
        organization_pk = self.kwargs.get("organization_pk")
        if organization_pk == "-1":
            allowed_sources = DataSource.objects.all()
        else:
            organization = get_object_or_404(
                self.request.user.accessible_organizations(), pk=organization_pk
            )
            allowed_sources = DataSource.objects.filter(
                Q(organization__isnull=True) | Q(organization=organization)
            )

        return ReportType.objects.filter(
            Q(source__in=allowed_sources) | Q(source__isnull=True)
        ).select_related("source", "counterreporttype")

    @action(methods=["GET"], detail=False, url_path="used")
    def used(self, request, organization_pk):
        extra_attrs = {}
        if request.GET.get("start_date"):
            extra_attrs["date__gte"] = request.GET["start_date"]
        if request.GET.get("end_date"):
            extra_attrs["date__lte"] = request.GET["end_date"]
        qs = self.get_queryset().filter(
            Exists(
                ImportBatch.objects.filter(
                    report_type=OuterRef("pk"), organization_id=organization_pk, **extra_attrs
                )
            )
        )
        return Response(self.get_serializer(qs, many=True).data)


class InterestGroupViewSet(ReadOnlyModelViewSet):
    queryset = InterestGroup.objects.all()
    serializer_class = InterestGroupSerializer

    @action(methods=["GET"], detail=True, url_path="definitions")
    def definitions(self, request, pk):
        ig = self.get_object()
        report_types_with_interest = (
            ReportType.objects.filter(reportinterestmetric__interest_group=ig)
            .filter(
                Q(superseded_by__isnull=False)
                | Q(
                    id__in=ReportType.objects.filter(superseded_by__isnull=False).values(
                        "superseded_by"
                    )
                )
                | Q(counterreporttype__isnull=False)
            )
            .distinct()
            .prefetch_related("superseded_by", "interest_metrics")
            .order_by("short_name")
        )
        return Response(
            InterestGroupDefinitionsSerializer(
                {"report_types": report_types_with_interest, "interest_group": ig}
            ).data
        )


class FlexibleSlicerBaseView(APIView):
    def create_slicer(self, request):
        try:
            slicer = FlexibleDataSlicer.create_from_params(request.query_params)
            slicer.use_clickhouse = request.USE_CLICKHOUSE
            if slicer.tag_roll_up:
                slicer.tag_filter = user_visible_tags(
                    request.user, selected_tag_class=slicer.tag_class
                )
            slicer.add_extra_organization_filter(request.user.accessible_organizations())
            if settings.DEBUG:
                pprint(slicer.config())
            slicer.check_params()
            return slicer
        except SlicerConfigError as e:
            raise BadRequestException(
                {"error": {"message": str(e), "code": e.code, "details": e.details}}
            ) from None


class FlexibleSlicerView(FlexibleSlicerBaseView):
    def get(self, request):
        slicer = self.create_slicer(request)
        try:
            part = request.query_params.get("part") if slicer.split_by else None
            if part:
                part = parse_b64json(part)
                if isinstance(part, list):
                    part = [e or None for e in part]  # convert 0 to None for django compatibility
                if settings.DEBUG:
                    print("part:", part)
            data = slicer.get_data(part=part, lang=request.user.language)
        except SlicerConfigError as e:
            return Response(
                {"error": {"message": str(e), "code": e.code, "details": e.details}},
                status=HTTP_400_BAD_REQUEST,
            )
        pagination = StandardResultsSetPagination()
        page = pagination.paginate_queryset(data, request)
        return pagination.get_paginated_response(page)


class FlexibleSlicerRemainderView(FlexibleSlicerBaseView):
    def get(self, request):
        slicer = self.create_slicer(request)
        try:
            part = request.query_params.get("part") if slicer.split_by else None
            if part:
                part = parse_b64json(part)
            data = slicer.get_remainder(part=part)
            return Response(data)
        except SlicerConfigError as e:
            return Response(
                {"error": {"message": str(e), "code": e.code, "details": e.details}},
                status=HTTP_400_BAD_REQUEST,
            )


class FlexibleSlicerPossibleValuesView(FlexibleSlicerBaseView):
    def get(self, request):
        dimension = request.query_params.get("dimension")
        if not dimension:
            return Response(
                {
                    "error": {
                        "message": 'the "dimension" param is required',
                        "code": SlicerConfigErrorCode.E105,
                    }
                },
                status=HTTP_400_BAD_REQUEST,
            )
        slicer = self.create_slicer(request)
        q = request.query_params.get("q")
        pks = None
        pks_value = request.query_params.get("pks")
        if pks_value:
            try:
                pks = list(map(int, pks_value.split(",")))
            except ValueError as e:
                return Response({"error": {"message": str(e)}})
        return Response(
            slicer.get_possible_dimension_values(
                dimension, ignore_self=True, text_filter=q, pks=pks
            )
        )


class FlexibleSlicerSplitParts(FlexibleSlicerBaseView):
    def get(self, request):
        slicer = self.create_slicer(request)
        count = 0
        use_clickhouse = request.USE_CLICKHOUSE  # may change in the course of the query
        if use_clickhouse:
            from logs.cubes import ch_backend

            try:
                qs = slicer.get_parts_queryset(use_clickhouse=True)
            except Exception as e:
                logger.error(
                    "Error when getting parts with clickhouse, falling back to django: "
                    f"{e}\n{traceback.format_exc()}"
                )
                async_mail_admins.delay(
                    "Error when getting parts with clickhouse (fallback to django applied)",
                    f"Error: {e}\n\n{traceback.format_exc()}",
                )
                use_clickhouse = False
                qs = slicer.get_parts_queryset()
            if qs:
                if not isinstance(qs, CubeQuery):
                    # clickhouse was not able to handle the query, we got a django queryset
                    use_clickhouse = False
                    count = qs.count()
                else:
                    count = ch_backend.get_count(qs)
        else:
            if qs := slicer.get_parts_queryset():
                count = qs.count()
        cropped = False
        if count:
            if count > slicer.MAXIMUM_POSSIBLE_PARTS:
                qs = qs[: slicer.MAXIMUM_POSSIBLE_PARTS]
                cropped = True
            # get values
            if use_clickhouse:
                # we need to convert 0 to None for django compatibility
                # and we remove the score field which is only available in clickhouse
                # we also strip the _id suffix from the keys if it is there,
                # bacause it is not present when using django backend
                values = [
                    {
                        k[:-3] if k.endswith("_id") else k: v or None
                        for k, v in rec._asdict().items()
                        if k != "score"
                    }
                    for rec in ch_backend.get_records(qs)
                ]
            else:
                values = qs
            return Response({"count": count, "values": values, "cropped": cropped})
        return Response({"count": 0, "values": [], "cropped": False})


class FlexibleSlicerCoverageView(FlexibleSlicerBaseView):
    def get(self, request):
        slicer = self.create_slicer(request)
        return Response(slicer.get_coverage())


class FlexibleReportViewSet(ModelViewSet):
    queryset = FlexibleReport.objects.none()
    serializer_class = FlexibleReportSerializer
    filter_backends = [PrimaryDimensionFlexiReportFilter]

    def get_queryset(self):
        return (
            FlexibleReport.objects.filter(
                Q(owner=self.request.user)  # owned by user
                | Q(owner__isnull=True, owner_organization__isnull=True)  # completely public
                | Q(
                    owner_organization__in=self.request.user.accessible_organizations()
                )  # assigned to owner's organization
            )
            .annotate(
                max_mailing_count=Count("flexiblereportuseremail")
            )  # upper bound for mailing count
            .select_related("owner", "owner_organization", "last_updated_by", "created_by")
        )

    def _preprocess_config(self, request):
        if "config" not in request.data:
            return None
        slicer = FlexibleDataSlicer.create_from_params(request.data.get("config"))
        return FlexibleReport.serialize_slicer_config(slicer.config())

    def _get_basic_data(self, request):
        owner = request.user.pk if "owner" not in request.data else request.data.get("owner")
        return {
            "owner": owner,
            "owner_organization": (request.data.get("owner_organization")),
            "name": request.data.get("name"),
            "description": request.data.get("description", ""),
        }

    def _check_write_permissions(self, request, owner, owner_organization):
        # only superuser can set other user as owner
        if not (request.user.is_superuser or request.user.is_admin_of_master_organization):
            if owner not in (None, request.user.pk):
                raise PermissionDenied(f"Not allowed to set owner {owner}")
        if owner_organization:
            rel = request.user.organization_relationship(owner_organization)
            if rel < REL_ORG_ADMIN:
                raise PermissionDenied(
                    f"Not allowed to set owner_organization {owner_organization}"
                )
        if not owner and not owner_organization:
            # this should be consortial access level
            if not (request.user.is_superuser or request.user.is_admin_of_master_organization):
                raise PermissionDenied("Not allowed to create consortial level report")

    def create(self, request, *args, **kwargs):
        config = self._preprocess_config(request)
        if config is None:
            return Response(
                {"error": 'Missing "config" parameter for the report'}, status=HTTP_400_BAD_REQUEST
            )
        data = {**self._get_basic_data(request), "report_config": config}
        self._check_write_permissions(request, data["owner"], data["owner_organization"])
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
                raise PermissionDenied("Not allowed to change private report")
        elif obj.access_level == FlexibleReport.Level.ORGANIZATION:
            # only admin of owner_organization or superuser may edit
            if not (user.is_superuser or user.is_admin_of_master_organization):
                rel = request.user.organization_relationship(obj.owner_organization_id)
                if rel < REL_ORG_ADMIN:
                    raise PermissionDenied("Not allowed to change organization report")
        else:
            # only superuser may edit consortium level reports
            if not (user.is_superuser or user.is_admin_of_master_organization):
                raise PermissionDenied("Not allowed to change consortial report")

        if not delete:
            # now more specific permissions about who can change access level
            # we deduce what the owner and owner_organization would be after the update takes place
            # and check if the current user is allowed to create such a report
            owner = request.data.get("owner") if "owner" in request.data else obj.owner_id
            owner_organization = (
                request.data.get("owner_organization")
                if "owner_organization" in request.data
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
            data["report_config"] = config
        serializer = self.get_serializer(report, data=data, partial=kwargs.get("partial"))
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=HTTP_200_OK, headers=headers)

    def destroy(self, request, *args, **kwargs):
        self._check_update_permissions(request, self.get_object(), delete=True)
        return super().destroy(request, *args, **kwargs)

    def _add_mailing_count(self, queryset, request):
        for rec in queryset:
            if rec.max_mailing_count > 0:
                rec.mailing_count = FlexibleReportUserEmail.objects.filter(
                    flexible_report=rec, user__in=self.view_users_queryset(rec, request.user)
                ).count()
            else:
                rec.mailing_count = 0

    def list(self, request, *args, **kwargs):
        """
        Custom list to add the mailing count to the response.
        Unfortunately, it has to be done object by object.
        """
        # The queryset is already annotated with the max_mailing_count which is an upper bound
        # for the mailing count. Thus if the value is 0, we can be sure that no mailing has been
        # created yet and we can skip the count query.
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            self._add_mailing_count(page, request)
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        self._add_mailing_count(queryset, request)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """
        Custom retrieve to add the mailing count to the response
        """
        instance = self.get_object()
        instance.mailing_count = FlexibleReportUserEmail.objects.filter(
            flexible_report=instance, user__in=self.view_users_queryset(instance, request.user)
        ).count()
        return Response(self.get_serializer(instance).data)

    def view_users_queryset(self, report: FlexibleReport, user: User):
        """
        Return a queryset of users that the current user can see as related to the report.
        """
        if user not in report.users_with_edit_access():
            # if the user does not have edit access, they can only see themselves
            return User.objects.filter(pk=user.pk)
        # if the user has edit access, they can see all other users with view access
        # but not (other) consortium admins
        consortium_admins = User.objects.filter_consortium_admins().exclude(pk=user.pk)
        return report.users_with_view_access().exclude(pk__in=consortium_admins).distinct()

    @action(methods=["GET"], detail=True, url_path="mailings", url_name="mailings")
    def list_mailings(self, request, pk):
        """
        List all report mailings for a given report
        """
        report: FlexibleReport = self.get_object()
        visible_users = self.view_users_queryset(report, request.user)
        frus = FlexibleReportUserEmail.objects.filter(
            flexible_report=report, user__in=visible_users
        ).select_related("user")

        return Response(FlexibleReportUserEmailSerializer(frus, many=True).data)

    @action(methods=["GET"], detail=True, url_path="view-users", url_name="view-users")
    def view_users(self, request, pk):
        """
        Return all users that can view the report, excluding other consortium admins.
        """
        return Response(
            UserSerializerForMailing(
                self.view_users_queryset(self.get_object(), request.user).order_by(
                    "last_name", "first_name", "email", "username", "pk"
                ),
                many=True,
            ).data
        )


class FlexibleReportUserEmailViewSet(ModelViewSet):
    serializer_class = FlexibleReportUserEmailSerializer
    filter_backends = [PrimaryDimensionFlexiReportFilter]

    def get_queryset(self):
        return FlexibleReportUserEmail.objects.filter(
            user__in=self.request.user.accessible_users()
        ).select_related("flexible_report")

    def get_serializer_class(self):
        if self.action == "create":
            return FlexibleReportUserEmailCreateSerializer
        return FlexibleReportUserEmailSerializer

    @action(methods=["POST"], detail=False, url_path="test")
    def test(self, request):
        """
        Just send the email, don't save the instance to the database
        """
        # pre-validate the data before sending it to the task
        serializer = FlexibleReportUserEmailCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # check permissions
        # check that the user has access to the report
        fr = serializer.validated_data["flexible_report"]
        target_user = serializer.validated_data["user"]
        if request.user not in fr.users_with_view_access():
            raise PermissionDenied("You do not have permission to perform this action.")
        # check that user can send to the target user
        if target_user not in request.user.accessible_users():
            raise PermissionDenied("You do not have permission to perform this action.")
        # check that the target user has access to the report
        if target_user not in fr.users_with_view_access():
            raise PermissionDenied("You do not have permission to perform this action.")

        send_report_mailing_raw_task.delay(request.data)
        return Response({"message": "Email sent", "success": True}, status=HTTP_200_OK)


class InterestComputationDescriptionView(APIView):
    """
    API endpoint that provides a comprehensive description of how interest is computed
    for a given organization or globally.

    This endpoint returns:
    - Organization information and interest configuration
    - Report type hierarchy showing which reports supersede others
    - Interest definitions showing which metrics define interest for each report type
    - Dimension mappings showing how source data is mapped to interest dimensions
    - Filters applied to source data to compute different types of interest
    - Summary statistics of the configuration
    """

    def get(self, request):
        """
        Get interest computation description for an organization or global settings.

        Query parameters:
        - organization_id: Optional organization ID. If not provided, returns global settings.
        """
        organization = None
        # Get organization if specified
        if organization_id := request.GET.get("organization_id"):
            if not request.user.accessible_organizations().filter(pk=organization_id).exists():
                raise PermissionDenied("You don't have access to this organization")
            organization = Organization.objects.get(pk=organization_id)
            interest_config = organization.get_interest_config()
        else:
            interest_config = InterestConfig.objects.default()

        interest_profile = interest_config.interest_profile

        # Get all report types that have interest definitions AND are part of the hierarchy
        # (either superseded by another report type or supersede another report type)
        report_types_with_interest = (
            ReportType.objects.filter(reportinterestmetric__isnull=False)
            .filter(
                Q(superseded_by__isnull=False)
                | Q(
                    id__in=ReportType.objects.filter(superseded_by__isnull=False).values(
                        "superseded_by"
                    )
                )
            )
            .distinct()
            .prefetch_related("superseded_by", "interest_metrics")
            .order_by("short_name")
        )

        # Get interest definitions for the profile
        interest_definitions = (
            ReportInterestMetric.objects.filter(
                Q(interest_profile=interest_profile) | Q(interest_profile__isnull=True),
                report_type__in=report_types_with_interest,
            )
            .select_related("metric", "interest_group", "interest_profile")
            .prefetch_related("filters__dimension")
        )

        # Get dimension mappings
        interest_rt = ReportType.objects.get_interest_rt()
        dimension_mappings = InterestDimensionValueMapping.objects.filter(
            interest_rtdim__report_type=interest_rt
        ).select_related(
            "interest_rtdim__dimension", "source_rtdim__dimension", "source_rtdim__report_type"
        )

        # Prepare response data
        response_data = {
            "organization": organization,
            "interest_config": interest_config,
            "report_type_hierarchy": list(report_types_with_interest),
            "interest_definitions": list(interest_definitions),
            "dimension_mappings": list(dimension_mappings),
        }

        # Serialize the response
        serializer = InterestComputationDescriptionSerializer(response_data)
        return Response(serializer.data)


class MduHeatmapDataView(MduAccessLogViewMixin, AccessLogListViewBase):
    def list(self, request, *args, **kwargs):
        mdu_id = self.kwargs["mdu_id"]
        mdu = get_object_or_404(ManualDataUpload.objects.select_related("report_type"), pk=mdu_id)
        queryset = self.get_base_queryset()

        monthly_data = (
            queryset.annotate(year=Extract("date", "year"), month=Extract("date", "month"))
            .values("year", "month")
            .annotate(
                total_value=Sum("value"),
                metric_count=Count("metric", distinct=True),
                record_count=Count("pk"),
            )
            .order_by("year", "month")
        )

        monthly_data_list = list(monthly_data)

        complete_monthly_data = []
        all_years = sorted(set(item["year"] for item in monthly_data_list))

        data_map = {f"{item['year']}-{item['month']}": item for item in monthly_data_list}

        for year in all_years:
            for month in range(1, 13):
                key = f"{year}-{month}"
                complete_monthly_data.append(
                    data_map.get(
                        key,
                        {
                            "year": year,
                            "month": month,
                            "total_value": None,
                            "metric_count": None,
                            "record_count": None,
                        },
                    )
                )

        metrics = (
            queryset.values_list("metric__short_name", flat=True)
            .distinct()
            .order_by("metric__short_name")
        )

        # map e.g. "dim1" to Dimension object
        pos_to_dim = {
            f"dim{e.position + 1}": e.dimension.short_name
            for e in ReportTypeToDimension.objects.filter(
                report_type=mdu.report_type
            ).select_related("dimension")
        }

        # annotate Max of DimensionTexts if dimX=None for all records, Max will be None
        ann = {f"{pos}_max": Max(pos) for pos in pos_to_dim.keys()}
        dim_max = queryset.aggregate(**ann)
        present_pos = {an_name[:-4] for an_name, an_max in dim_max.items() if an_max}
        # filter the dimensions
        dimensions_with_data = [dim for pos, dim in pos_to_dim.items() if pos in present_pos]

        return Response(
            {
                "monthly_data": complete_monthly_data,
                "metrics": list(metrics),
                "dimensions": list(dimensions_with_data),
            }
        )
