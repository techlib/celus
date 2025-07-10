import typing
from itertools import chain

from allauth.utils import build_absolute_uri
from api.auth import extract_org_from_request_api_key
from api.permissions import HasOrganizationAPIKey
from charts.models import ReportDataView
from charts.serializers import ReportDataViewSerializer
from core.exceptions import BadRequestException
from core.filters import PkMultiValueFilterBackend
from core.logic.dates import date_filter_from_params, parse_month
from core.logic.type_conversion import to_bool
from core.models import DataSource
from core.pagination import SmartPageNumberPagination
from core.permissions import SuperuserOrAdminPermission, ViewPlatformPermission
from django.conf import settings
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Count, Exists, FilteredRelation, OuterRef, Prefetch, Q, Sum
from django.db.models.functions import Coalesce
from hcube.api.models.aggregation import ArrayAgg as HArrayAgg
from hcube.api.models.aggregation import Count as CubeCount
from hcube.api.models.aggregation import Sum as HSum
from logs.cubes import AccessLogCube, ch_backend
from logs.filters import OrderByFilter
from logs.logic.interest.structure import (
    get_interest_metrics,
    get_interest_metrics_implying_availability,
)
from logs.logic.queries import replace_report_type_with_materialized
from logs.models import AccessLog, InterestConfig, InterestGroup, Metric, ReportType
from logs.serializers import ReportTypeExtendedSerializer
from logs.views import StandardResultsSetPagination
from nibbler.models import ParserDefinition
from organizations.logic.queries import (
    extend_query_filter,
    get_organization_related_accesslog_filters_for_interest,
    organization_filter_from_org_id,
)
from organizations.models import Organization, OrganizationAltName
from organizations.serializers import OrganizationAltNameSerializer
from pandas import DataFrame
from recache.util import recache_queryset
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, UpdateModelMixin
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.status import HTTP_202_ACCEPTED
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ReadOnlyModelViewSet, ViewSet
from rest_pandas import PandasCSVRenderer, PandasExcelRenderer
from sushi.models import CounterReportPlatform
from tags.models import Tag

from config.permissions import IsAuthenticatedWithOptional2FA
from publications.models import (
    CounterReportSource,
    Item,
    Platform,
    PlatformTitle,
    Title,
    TitleOverlapBatch,
    TitleOverlapBatchState,
)
from publications.serializers import (
    DeleteAllDataPlatformSerializer,
    ItemSerializer,
    SimplePlatformSerializer,
    TitleCountSerializer,
    TitleOverlapBatchCreateSerializer,
    TitleOverlapBatchSerializer,
    UseCaseSerializer,
)

from .filters import PlatformFilter, PubTypeFilter
from .logic.use_cases import get_use_cases
from .serializers import AllPlatformSerializer, PlatformSerializer, TitleSerializer
from .tasks import (
    delete_platform_data_task,
    erms_sync_platforms_task,
    process_title_overlap_batch_task,
)


class SmartResultsSetPagination(StandardResultsSetPagination, SmartPageNumberPagination):
    pass


class AllPlatformsViewSet(ReadOnlyModelViewSet):
    permission_classes = [ViewPlatformPermission]

    serializer_class = AllPlatformSerializer
    filter_backends = [PlatformFilter]

    @classmethod
    def _organization_pk_to_obj(cls, organization_pk):
        try:
            organization_pk = int(organization_pk)
        except ValueError as exc:
            raise ValidationError(
                detail=f'Bad value for the "organization_pk" param: "{str(exc)}"'
            ) from None
        if organization_pk and organization_pk != -1:
            return Organization.objects.get(pk=organization_pk)
        else:
            # all organizations were requested using -1
            return None

    def get_queryset(self):
        """Returns Platforms which can be displayed to the user"""
        organization = self._organization_pk_to_obj(self.kwargs.get("organization_pk"))

        return (
            self.request.user.accessible_platforms(organization=organization)
            .select_related("source", "source__organization")
            .prefetch_related(
                Prefetch(
                    "counterreportplatform_set",
                    queryset=CounterReportPlatform.objects.select_related(
                        "counter_report", "platform"
                    ),
                )
            )
            .order_by("name")
            .annotate(
                has_raw_parser=Exists(
                    ParserDefinition.objects.filter(
                        source_id=OuterRef("source_id"),
                        platforms__contains=[OuterRef("short_name")],
                    )
                )
            )
        )

    @action(detail=False, url_path="use-cases", serializer_class=UseCaseSerializer)
    def use_cases(self, request, organization_pk):
        """Returns data how are the platforms successfully used"""
        platforms = self.get_queryset()
        use_cases = get_use_cases(platforms)
        serializer = UseCaseSerializer(data=list(use_cases), many=True)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)

    @action(detail=True, url_path="report-types")
    def get_report_types(self, request, pk, organization_pk):
        """
        Provides a list of report types associated with this platform + list of all COUNTER reports.
        This view represents all the reports that may be manually uploaded to a platform.

        It is only used when data are uploaded manually to a platform in the CELUS format.
        """
        organization = self._organization_pk_to_obj(organization_pk)
        # the following line is a sanity check to make sure the platform belongs to the organization
        # but the platform itself is not part of the computation because with the new interest
        # there is no connection between platforms and report types
        get_object_or_404(request.user.accessible_platforms(organization=organization), pk=pk)
        # We show all the reports that are not created by other organizations.
        # => all where the source is not other organizations private_data_source
        conditions = Q(source__isnull=True) | ~Q(source__type=DataSource.TYPE_ORGANIZATION)
        if organization:
            conditions |= Q(source__organization=organization)
        report_types = (
            ReportType.objects.filter(conditions)
            .distinct()
            .select_related("counterreporttype")
            .prefetch_related(
                "reportinterestmetric_set__metric",
                "reportinterestmetric_set__interest_group",
                "source",
                "source__organization",
                "controlled_metrics",
            )
        )

        return Response(ReportTypeExtendedSerializer(report_types, many=True).data)


class PlatformViewSet(CreateModelMixin, UpdateModelMixin, ReadOnlyModelViewSet):
    serializer_class = PlatformSerializer

    def get_permissions(self):
        permission_classes = list(self.permission_classes)

        def generate_permission(organization_id: int):
            action = self.action

            # Create admin permission for given organization
            class Permission(IsAuthenticatedWithOptional2FA):
                def has_permission(self, request, *args, **kwargs):
                    # Deleting all data should be enabled regardless
                    # of ALLOW_USER_CREATED_PLATFORMS flag
                    if action != "delete_all_data" and not settings.ALLOW_USER_CREATED_PLATFORMS:
                        return False
                    return request.user.has_organization_admin_permission(int(organization_id))

            return Permission

        if self.action in ["create", "delete_all_data"]:
            organization_id = self.kwargs["organization_pk"]
            Permission = generate_permission(organization_id)
            permission_classes = [
                SuperuserOrAdminPermission | (e & Permission) for e in permission_classes
            ]
        elif self.action in ["update", "partial_update"]:
            obj = get_object_or_404(Platform, pk=self.kwargs["pk"])
            if obj.source and obj.source.organization:
                Permission = generate_permission(obj.source.organization.pk)
                permission_classes = [
                    SuperuserOrAdminPermission | (e & Permission) for e in permission_classes
                ]
            else:
                permission_classes = [SuperuserOrAdminPermission]

        return [permission() for permission in permission_classes]

    def _short_name_check(
        self,
        short_name: str,
        source: typing.Optional[DataSource],
        instance_pk: typing.Optional[int],
    ):
        if (
            Platform.objects.filter(
                Q(short_name=short_name) & (Q(source__isnull=True) | Q(source=source))
            )
            .exclude(pk=instance_pk)
            .exists()
        ):
            raise ValidationError({"short_name": "Already exists"}, code="unique")

    @transaction.atomic
    def perform_create(self, serializer):
        if self.kwargs["organization_pk"] != "-1":
            organization = get_object_or_404(Organization, pk=self.kwargs["organization_pk"])
            source = organization.get_or_create_private_source()
        else:
            source = None

        serializer.is_valid()  # -> sets validated_data
        self._short_name_check(serializer.validated_data["short_name"], source, None)
        platform = serializer.save(ext_id=None, source=source)

        # Update related report types based on knowledgebase
        if platform.counter_reports_source == CounterReportSource.KNOWLEDGEBASE:
            Platform.objects.filter(pk=platform.pk).update_counter_reports_from_knowledgebase()

    def perform_update(self, serializer):
        serializer.is_valid()  # -> sets validated_data
        platform = self.get_object()
        if "short_name" in serializer.validated_data:
            self._short_name_check(
                serializer.validated_data["short_name"], platform.source, platform.pk
            )
        serializer.save(
            ext_id=None, source=self.get_object().source
        )  # source can be selected only on create

        # Update related report types based on knowledgebase
        if serializer.instance.counter_reports_source == CounterReportSource.KNOWLEDGEBASE:
            Platform.objects.filter(pk=platform.pk).update_counter_reports_from_knowledgebase()

        #  update sushi credential's counter reports
        serializer.instance.sushicredentials_set.update_report_types_based_on_platform()

    def get_queryset(self):
        """
        Should return only platforms for the requested organization
        """
        org_filter = organization_filter_from_org_id(
            self.kwargs.get("organization_pk"), self.request.user
        )
        if org_filter:
            qs = Platform.objects.filter(
                Q(**org_filter)
                | Q(**extend_query_filter(org_filter, "sushicredentials__"))
                | Q(**extend_query_filter(org_filter, "source__"))
            ).distinct()
        # only those that have an organization connected
        elif "used_only" in self.request.query_params:
            qs = Platform.objects.filter(
                Q(organization__isnull=False)
                | Q(sushicredentials__isnull=False)
                | Q(source__organization__isnull=False)
            ).distinct()
        else:
            qs = Platform.objects.all()
        return qs.select_related("source", "source__organization")

    @action(methods=["GET"], url_path="title-count", url_name="title-count", detail=False)
    def title_count(self, request, organization_pk):
        date_filter_params = date_filter_from_params(request.GET)
        if request.USE_CLICKHOUSE:
            org_filter = organization_filter_from_org_id(
                organization_pk, request.user, clickhouse=True
            )
            query = (
                AccessLogCube.query()
                .filter(**org_filter, **date_filter_params)
                .group_by("platform_id")
                .order_by("platform_id")
                .filter(target_id__not_in=[0])
                .aggregate(title_count=CubeCount(distinct="target_id"))
            )
            return Response(
                {"platform": rec.platform_id, "title_count": rec.title_count}
                for rec in ch_backend.get_records(query, auto_use_materialized_views=True)
            )
        else:
            org_filter = organization_filter_from_org_id(organization_pk, request.user)
            qs = (
                PlatformTitle.objects.filter(**org_filter, **date_filter_params)
                .values("platform")
                .annotate(title_count=Count("title", distinct=True))
            )
            return Response(qs)

    @action(methods=["GET"], url_path="title-count", url_name="title-count", detail=True)
    def title_count_detail(self, request, organization_pk, pk):
        org_filter = organization_filter_from_org_id(organization_pk, request.user)
        date_filter_params = date_filter_from_params(request.GET)
        qs = (
            PlatformTitle.objects.filter(platform_id=pk, **org_filter, **date_filter_params)
            .values("platform")
            .annotate(title_count=Count("title", distinct=True))
        )
        try:
            result = qs.get()
            title_count = result.get("title_count", 0)
        except PlatformTitle.DoesNotExist:
            title_count = 0
        return Response({"title_count": title_count})

    @action(methods=["GET"], url_path="title-ids-list", url_name="title-ids-list", detail=False)
    def title_id_list(self, request, organization_pk):
        org_filter = organization_filter_from_org_id(organization_pk, request.user)
        date_filter_params = date_filter_from_params(request.GET)
        pub_type_arg = self.request.query_params.get("pub_type")
        search_filters = []
        if pub_type_arg:
            search_filters.append(Q(title__pub_type__in=pub_type_arg.split(",")))
        qs = (
            PlatformTitle.objects.filter(*search_filters, **org_filter, **date_filter_params)
            .values_list("platform_id", "title_id")
            .distinct()
        )
        result = {}
        for platform_id, title_id in qs:
            if platform_id not in result:
                result[platform_id] = []
            result[platform_id].append(title_id)
        return Response(result)

    @action(methods=["POST"], url_path="delete-all-data", url_name="delete-all-data", detail=True)
    def delete_all_data(self, request, pk, organization_pk):
        org_filter = organization_filter_from_org_id(
            organization_pk, request.user, prefix=None, admin_required=True
        )
        serializer = DeleteAllDataPlatformSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        org_ids = [org.pk for org in Organization.objects.filter(**org_filter)]
        delete_platform = serializer.validated_data.get("delete_platform", False)
        platform = get_object_or_404(Platform.objects.all(), pk=pk)
        if delete_platform:
            # to perform delete, platform should belong to the organization
            if not platform.source or int(organization_pk) != platform.source.organization.pk:
                raise ValidationError(
                    detail=f'Platform "{platform}" does not belong to organization'
                    f" #{organization_pk}"
                )
        delete_credentials = serializer.validated_data.get("delete_credentials", False)

        task = delete_platform_data_task.delay(pk, org_ids, delete_platform, delete_credentials)
        return Response({"success": True, "task_id": task.id})


class PlatformInterestViewSet(ViewSet):
    renderer_classes = [JSONRenderer, PandasCSVRenderer, PandasExcelRenderer]

    @classmethod
    def get_report_type_and_filters(cls):
        interest_rt = ReportType.objects.get_interest_rt()
        interest_metrics = get_interest_metrics()
        interest_annot_params = {
            im.short_name: Coalesce(Sum("value", filter=Q(metric=im)), 0) for im in interest_metrics
        }
        return interest_rt, interest_annot_params

    def get_queryset(self, request, organization_pk):
        org_filters, exclude_filters = get_organization_related_accesslog_filters_for_interest(
            organization_pk, request.user
        )
        date_filter_params = date_filter_from_params(request.GET)
        interest_rt, interest_annot_params = self.get_report_type_and_filters()
        accesslog_filter = {"report_type": interest_rt, **org_filters, **date_filter_params}
        replace_report_type_with_materialized(
            accesslog_filter, other_used_dimensions=exclude_filters.keys()
        )
        result = (
            AccessLog.objects.filter(**accesslog_filter)
            .exclude(**exclude_filters)
            .values("platform")
            .annotate(**interest_annot_params)
        )
        return result

    def list(self, request, organization_pk):
        qs = self.get_queryset(request, organization_pk)
        data_format = request.GET.get("format")
        if data_format in ("csv", "xlsx"):
            # when exporting, we want to rename the columns and rows
            data = DataFrame(qs)
            platform_names = {
                pl["pk"]: pl["short_name"]
                for pl in Platform.objects.all().values("pk", "short_name")
            }
            metric_names = {
                m["short_name"]: m["name"]
                for m in InterestGroup.objects.all().values("short_name", "name")
            }
            if "platform" in data:
                data["platform"] = [platform_names[pk] for pk in data["platform"]]
                data.set_index("platform", drop=True, inplace=True)
                data.rename(columns=metric_names, inplace=True)
            return Response(
                data,
                headers={"Content-Disposition": f'attachment; filename="export.{data_format}"'},
            )
        return Response(qs)

    def retrieve(self, request, organization_pk, pk):
        qs = self.get_queryset(request, organization_pk)
        data = qs.filter(platform_id=pk)
        if data:
            return Response(data[0])
        return Response({})

    def _get_by_year_data(self, request, organization_pk, platform_id=None):
        """Helper method to get interest data grouped by year.

        Args:
            request: The request object
            organization_pk: The organization primary key
            platform_id: Optional platform ID to filter by

        Returns:
            QuerySet with interest data grouped by year
        """
        interest_rt, interest_annot_params = self.get_report_type_and_filters()
        org_filters, exclude_filters = get_organization_related_accesslog_filters_for_interest(
            organization_pk, request.user
        )
        accesslog_filter = {"report_type": interest_rt, **org_filters}
        if platform_id:
            accesslog_filter["platform_id"] = platform_id

        replace_report_type_with_materialized(
            accesslog_filter, other_used_dimensions=exclude_filters.keys()
        )
        values = ["date__year"]
        if not platform_id:
            values.append("platform")

        return (
            AccessLog.objects.filter(**accesslog_filter)
            .exclude(**exclude_filters)
            .values(*values)
            .annotate(**interest_annot_params)
        )

    @action(detail=True, url_path="by-year")
    def by_year(self, request, pk, organization_pk):
        result = self._get_by_year_data(request, organization_pk, platform_id=pk)
        return Response(result)

    @action(detail=False, url_path="by-year")
    def list_by_year(self, request, organization_pk):
        result = self._get_by_year_data(request, organization_pk)
        return Response(result)


class GlobalPlatformsViewSet(ReadOnlyModelViewSet):
    permission_classes = [ViewPlatformPermission | HasOrganizationAPIKey]
    serializer_class = SimplePlatformSerializer
    queryset = Platform.objects.all()
    filter_backends = [PkMultiValueFilterBackend]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_anonymous:
            # Anonymous user must use api-key based authentication otherwise he would not get here
            organization = extract_org_from_request_api_key(self.request)
            if organization:
                return qs.filter(
                    Q(organizationplatform__organization=organization)
                    | Q(sushicredentials__organization=organization)
                ).distinct()
            else:
                # this should not happen, but just to make sure
                raise PermissionDenied(
                    "cannot access the view without api key or session based authentication"
                )
        else:
            qs = qs.filter(pk__in=self.request.user.accessible_platforms())
        return qs.order_by("name")


class GlobalTitleViewSet(ReadOnlyModelViewSet):
    serializer_class = TitleSerializer
    queryset = Title.objects.all()
    pagination_class = StandardResultsSetPagination
    filter_backends = [PkMultiValueFilterBackend]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.order_by("name")


class BaseTitleViewSet(ReadOnlyModelViewSet):
    serializer_class = TitleSerializer
    renderer_classes = [JSONRenderer, PandasCSVRenderer, PandasExcelRenderer]
    # pagination_class = StandardResultsSetPagination

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.org_filter = None
        self.date_filter = None
        # the queryset used to select relevant titles - stored for usage elsewhere,
        # e.g. in postprocessing
        self.title_selection_query = None

    def _extra_filters(self):
        return {}

    def _extra_accesslog_filters(self) -> typing.Tuple[dict, dict]:
        """
        Returns a tuple of two dictionaries. The first dictionary contains the filters
        that are used to filter the accesslog. The second dictionary contains the filters
        that are used to exclude the accesslog.
        """
        return {}, {}

    def _annotations(self):
        return {}

    def _postprocess(self, result):
        return result

    def _postprocess_paginated(self, result):
        return result

    def _before_queryset(self):
        pass

    def get_queryset(self):
        """
        Should return only titles for specific organization and platform
        """
        self.org_filter = organization_filter_from_org_id(
            self.kwargs.get("organization_pk"), self.request.user
        )
        self.date_filter = date_filter_from_params(self.request.GET)
        # run stuff before we start creating the queryset
        self._before_queryset()
        # put together filters for title itself
        search_filters = []
        q = self.request.query_params.get("q")
        if q:
            search_filters = [
                Q(name__ilike=p)
                | Q(isbn__ilike=p)
                | Q(eissn__ilike=p)
                | Q(issn__ilike=p)
                | Q(doi__ilike=p)
                for p in q.split()
            ]
        pub_type_arg = self.request.query_params.get("pub_type")
        if pub_type_arg:
            search_filters.append(Q(pub_type=pub_type_arg))
        # tags

        # tags
        if tag_arg := self.request.query_params.get("tags"):
            tag_ids = map(int, tag_arg.split(","))
            search_filters.append(
                Q(
                    tags__in=Tag.objects.user_accessible_tags(self.request.user).filter(
                        pk__in=tag_ids
                    )
                )
            )
        # we evaluate this here as it might be important for the _extra_accesslog_filters method
        extra_filters = self._extra_filters()
        # put together filters for accesslogs
        # because this view is about titles, not accesslogs, the accesslog filters are
        # here only for annotation purposes. Thus it is assumed that when a sub-class
        # (or mixin) implements `_extra_accesslog_filters`, it will use the filtered
        # accesslogs stored in `relevant_accesslogs` field for additional annotations
        # (such as summing them up) by implementing the `_annotations` method.
        # It does not make sense otherwise.
        accesslog_filter, exclude_filters = self._extra_accesslog_filters()
        title_qs = Title.objects.all()
        if accesslog_filter or exclude_filters:
            # we have some filters for accesslog - this means we have to add the relevant
            # accesslogs to the queryset
            accesslog_filter.update(**extend_query_filter(self.date_filter, "accesslog__"))
            condition = Q(**accesslog_filter)
            if exclude_filters:
                condition &= ~Q(**exclude_filters)
            title_qs = title_qs.annotate(
                relevant_accesslogs=FilteredRelation("accesslog", condition=condition)
            )
        # construct the whole query
        # joining together platformtitle and accesslog is problematic, because there are
        # usually several platformtitles and thus the join multiplies the number of joined
        # accesslogs and the sums are then multiplied as well.
        # because of this, we preselect the titles and then use the distinct IDs as base
        # for the query containing the sums
        # as a side effect, the query is also faster ;)
        base_title_query = Title.objects.filter(
            *search_filters,
            **extend_query_filter(self.date_filter, "platformtitle__"),
            **extend_query_filter(self.org_filter, "platformtitle__"),
            **extra_filters,
        )
        base_title_query = base_title_query.distinct().order_by()
        self.title_selection_query = base_title_query
        result = title_qs.filter(pk__in=base_title_query)
        annot = self._annotations()
        if annot:
            result = result.annotate(**annot)
        result = self._postprocess(result.order_by("name", "pub_type"))
        return result

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)

            if self.request.GET.get("format") in ("csv", "xlsx"):
                # for CSV and XLSX formats, we return a DataFrame and DRF takes care of the rest
                data = []
                for rec in serializer.data:
                    # inline interests
                    interest = rec.pop("interests")
                    rec.update(interest)
                    data.append(rec)
                data = DataFrame(data)
                return Response(data)

            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def paginate_queryset(self, queryset):
        qs = super().paginate_queryset(queryset)
        return self._postprocess_paginated(qs)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        self._postprocess_paginated([instance])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class TitleInterestBriefViewSet(ReadOnlyModelViewSet):
    def get_queryset(self):
        """
        Should return only titles for specific organization and platform
        """
        org_filters, exclude_filters = get_organization_related_accesslog_filters_for_interest(
            self.kwargs.get("organization_pk"), self.request.user
        )
        date_filter = date_filter_from_params(self.request.GET)
        interest_rt = ReportType.objects.get_interest_rt()
        metric_ids = [m.pk for m in get_interest_metrics_implying_availability()]

        search_filters = []
        pub_type_arg = self.request.query_params.get("pub_type")
        if pub_type_arg:
            search_filters.append(Q(target__pub_type__in=pub_type_arg.split(",")))
        queryset = (
            AccessLog.objects.filter(
                *search_filters,
                report_type=interest_rt,
                metric_id__in=metric_ids,  # only those interest types which imply availability
                **date_filter,
                **org_filters,
            )
            .exclude(**exclude_filters)
            .values("target_id")
            .exclude(target_id__isnull=True)
            .annotate(interest=Sum("value"))
        )
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        data = queryset.filter(interest__gt=0).order_by().values("target_id", "interest")
        return Response(data)

    def retrieve(self, request, pk, *args, **kwargs):
        queryset = self.get_queryset()
        data = get_object_or_404(queryset.order_by().values("interest"), target_id=pk)
        return Response(data)


class PlatformTitleViewSet(BaseTitleViewSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.platform = None

    def _extra_filters(self):
        filters = super()._extra_filters()
        self.platform = get_object_or_404(
            Platform.objects.filter(**self.org_filter), pk=self.kwargs["platform_pk"]
        )
        # filters['accesslog__platform'] = platform
        filters["platformtitle__platform"] = self.platform
        return filters


class TitleInterestMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.interest_rt = None
        self.interest_metrics = None

    def _before_queryset(self):
        self.interest_rt = ReportType.objects.get_interest_rt()
        self.interest_metrics = get_interest_metrics()

    def _extra_accesslog_filters(self):
        filters, exclude_filters = super()._extra_accesslog_filters()
        filters["accesslog__report_type_id"] = self.interest_rt.pk
        if hasattr(self, "platform") and self.platform:
            filters["accesslog__platform_id"] = self.platform.pk
        if self.org_filter:
            filters["accesslog__organization_id"] = self.org_filter.get("organization__pk")
            org = Organization.objects.get(pk=self.org_filter["organization__pk"])
            ic = org.get_interest_config()
        else:
            ic = InterestConfig.objects.default()
        interest_filters, negated_interest_filters = ic.get_interest_filters()
        interest_filters = extend_query_filter(interest_filters, "accesslog__")
        negated_interest_filters = extend_query_filter(negated_interest_filters, "accesslog__")
        filters.update(**interest_filters)
        exclude_filters.update(**negated_interest_filters)
        return filters, exclude_filters

    def _annotations(self):
        annotations = super()._annotations()
        interest_annot_params = {
            im.short_name: Coalesce(
                Sum("relevant_accesslogs__value", filter=Q(relevant_accesslogs__metric=im)), 0
            )
            for im in self.interest_metrics
        }
        annotations.update(interest_annot_params)
        return annotations

    def _postprocess_paginated(self, result):
        result = super()._postprocess_paginated(result)
        interest_types = {im.short_name for im in self.interest_metrics}
        for record in result:
            record.interests = {it: getattr(record, it) for it in interest_types}
        return result

    def _postprocess(self, result):
        order_by = self.request.query_params.get("order_by")
        if order_by == "tags":
            raise BadRequestException("Ordering by tags is not supported")
        desc = self.request.query_params.get("desc", "true")
        if order_by:
            prefix = "-" if desc == "true" else ""
            result = result.order_by(prefix + order_by, prefix + "pk")
        return result


class PlatformTitleInterestViewSet(TitleInterestMixin, PlatformTitleViewSet):
    serializer_class = TitleCountSerializer
    pagination_class = SmartResultsSetPagination


class BaseReportDataViewViewSet(ReadOnlyModelViewSet):
    """
    Provides a list of virtual report types
    """

    serializer_class = ReportDataViewSerializer
    # if we should do extra queries to ensure report views are really relevant
    more_precise_results = True

    def _extra_filters(self, org_filter):
        return {}

    def get_queryset(self):
        org_filter = organization_filter_from_org_id(
            self.kwargs.get("organization_pk"), self.request.user
        )
        extra_filters = self._extra_filters(org_filter)
        if self.request.USE_CLICKHOUSE:
            org_filter = organization_filter_from_org_id(
                self.kwargs.get("organization_pk"), self.request.user, clickhouse=True
            )
            extra_filters = {k + "_id": v.pk for k, v in extra_filters.items()}
            distinct_rts = {
                rec.report_type_id
                for rec in ch_backend.get_records(
                    AccessLogCube.query()
                    .filter(**org_filter, **extra_filters)
                    .group_by("report_type_id")
                )
            }
        else:
            access_log_filter = Q(**org_filter, **extra_filters)
            distinct_rts = set(
                AccessLog.objects.filter(access_log_filter)
                .exclude(report_type__materialization_spec__isnull=False)
                .values_list("report_type_id", flat=True)
                .distinct()
            )
        report_views = list(
            ReportDataView.objects.filter(base_report_type_id__in=distinct_rts).order_by("position")
        )
        # create proxy report view for each RT that has no report view
        rts_with_view = {rv.base_report_type_id for rv in report_views}
        to_fake = distinct_rts - rts_with_view
        for i, rt in enumerate(ReportType.objects.filter(id__in=to_fake)):
            # we use the fact that most attrs are the same in report type and report view
            rt.position = len(report_views) + i
            rt.is_proxy = True
            rt.is_standard_view = False
            report_views.append(rt)
        return report_views


class TitleReportDataViewViewSet(BaseReportDataViewViewSet):
    """
    Provides a list of report types for specific title for specific organization
    """

    def _extra_filters(self, org_filter):
        title = get_object_or_404(Title.objects.all(), pk=self.kwargs["title_pk"])
        return {"target": title}


class ItemReportDataViewViewSet(BaseReportDataViewViewSet):
    """
    Provides a list of report types for specific title for specific organization
    """

    def _extra_filters(self, org_filter):
        item = get_object_or_404(Item.objects.all(), pk=self.kwargs["item_pk"])
        out = {"item": item}
        if "title_pk" in self.kwargs:
            title = get_object_or_404(Title.objects.all(), pk=self.kwargs["title_pk"])
            out["target"] = title
        if platform_id := self.kwargs.get("platform_pk"):
            out["platform"] = get_object_or_404(Platform.objects.all(), pk=platform_id)
        return out


class PlatformReportDataViewViewSet(BaseReportDataViewViewSet):
    """
    Provides a list of report types for specific organization and platform
    """

    def _extra_filters(self, org_filter):
        platform = get_object_or_404(
            Platform.objects.filter(**org_filter), pk=self.kwargs["platform_pk"]
        )
        return {"platform": platform}


class PlatformTitleReportDataViewViewSet(BaseReportDataViewViewSet):
    """
    Provides a list of report types for specific title for specific organization and platform
    """

    def _extra_filters(self, org_filter):
        platform = get_object_or_404(
            Platform.objects.filter(**org_filter), pk=self.kwargs["platform_pk"]
        )
        title = get_object_or_404(Title.objects.all(), pk=self.kwargs["title_pk"])
        return {"target": title, "platform": platform}


class TitleViewSet(BaseTitleViewSet):
    serializer_class = TitleSerializer

    @action(detail=True, url_path="platforms")
    def platforms(self, request, pk, organization_pk):
        title = get_object_or_404(Title.objects.all(), pk=pk)
        org_filter = organization_filter_from_org_id(organization_pk, self.request.user)
        date_filter_params = date_filter_from_params(self.request.GET, key_start="accesslog__")
        platforms = Platform.objects.filter(
            accesslog__target=title,
            **date_filter_params,
            **extend_query_filter(org_filter, "accesslog__"),
        ).distinct()
        return Response(PlatformSerializer(platforms, many=True).data)


class TitleInterestViewSet(TitleInterestMixin, BaseTitleViewSet):
    """
    View for all titles with interest annotation
    """

    serializer_class = TitleCountSerializer
    pagination_class = SmartResultsSetPagination


class TopTitleInterestViewSet(ReadOnlyModelViewSet):
    """
    Optimized view to get top 10 titles for a particular type of interest.

    It does the same as `TitleInterestViewSet` but uses a simplified query. The reason is
    not so much to be faster, but to get around a bug in Django, which prevents `recache_query`
    from working properly for `TitleInterestViewSet`. Details about the error are available
    here: https://code.djangoproject.com/ticket/31926
    """

    serializer_class = TitleCountSerializer

    def get_queryset(self):
        interest_rt = ReportType.objects.get_interest_rt()
        interest_metrics = get_interest_metrics()
        interest_type_name = self.request.query_params.get("order_by", "full_text")

        # -- title filters --
        # publication type filter
        pub_type_arg = self.request.query_params.get("pub_type")

        # -- accesslog filters --
        # filtering only interest related accesslogs
        try:
            interest_metric = interest_metrics.get(short_name=interest_type_name)
        except Metric.DoesNotExist:
            raise BadRequestException(
                detail=f'Interest type "{interest_type_name}" does not exist'
            ) from None
        # date filter
        date_filter = date_filter_from_params(self.request.GET)

        # -- interest config --
        org_filters, exclude_filters = get_organization_related_accesslog_filters_for_interest(
            self.kwargs.get("organization_pk"),
            self.request.user,
            clickhouse=self.request.USE_CLICKHOUSE,
        )

        if self.request.USE_CLICKHOUSE and not pub_type_arg:
            negated_filters = {
                f"{k.split('__')[0]}__not_in": v
                for k, v in exclude_filters.items()
                if k.endswith("__in")
            }
            query = (
                AccessLogCube.query()
                .filter(
                    report_type_id=interest_rt.pk,
                    metric_id=interest_metric.pk,
                    target_id__not_in=[0],
                    **org_filters,
                    **negated_filters,
                )
                .group_by("target_id")
                .aggregate(**{interest_type_name: HSum("value")})
                .order_by(f"-{interest_type_name}")
            )
            if date_filter:
                query.filter(**date_filter)
            if pub_type_arg:
                raise ValueError("pub_type filter not supported in CH yet")
            ch_result = list(ch_backend.get_records(query[:10]))
            title_pks = [rec.target_id for rec in ch_result]
            pk_to_title = {title.pk: title for title in Title.objects.filter(pk__in=title_pks)}
            out = []
            for rec in ch_result[:10]:
                title = pk_to_title[rec.target_id]
                title.interests = {interest_type_name: getattr(rec, interest_type_name)}
                out.append(title)
            return out
        else:
            filters = {}
            interest_annot_params = {interest_type_name: Coalesce(Sum("accesslog__value"), 0)}
            filters["accesslog__report_type_id"] = interest_rt.pk
            filters["accesslog__metric"] = interest_metric
            if org_filters:
                filters.update(extend_query_filter(org_filters, "accesslog__"))
            if pub_type_arg:
                if self.request.USE_CLICKHOUSE:
                    print("`pub_type` filter not supported in ClickHouse yet.")
                filters["pub_type"] = pub_type_arg
            # date filter
            date_filter = extend_query_filter(date_filter, "accesslog__")

            records = (
                Title.objects.all()
                .filter(**date_filter, **filters)
                .exclude(**extend_query_filter(exclude_filters, "accesslog__"))
                .annotate(**interest_annot_params)
                .order_by(f"-{interest_type_name}")
            )[:10]
            # we recache the final queryset so that the results are automatically re-evaluated in
            # the background when needed
            records = recache_queryset(records, origin=f"top-10-titles-{interest_type_name}")
            for record in records:
                record.interests = {interest_type_name: getattr(record, interest_type_name)}
            return records


class InterestByPlatformMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.interest_rt = None
        # only use those platforms that have at least one title
        # when filtering by organization, organization filter will be applied later in
        # _before_queryset
        self.all_platforms = Platform.objects.filter(
            Exists(PlatformTitle.objects.filter(platform_id=OuterRef("pk")))
        )

    def _before_queryset(self):
        self.interest_rt = ReportType.objects.get_interest_rt()
        if self.org_filter:
            self.all_platforms = Platform.objects.filter(
                Exists(PlatformTitle.objects.filter(platform_id=OuterRef("pk"), **self.org_filter))
            )

    def _extra_accesslog_filters(self):
        filters, exclude_filters = super()._extra_accesslog_filters()
        filters["accesslog__report_type_id"] = self.interest_rt.pk
        if self.org_filter:
            filters["accesslog__organization_id"] = self.org_filter.get("organization__pk")
        return filters, exclude_filters

    def _annotations(self):
        annotations = super()._annotations()
        interest_annot_params = {
            f"pl_{platform.pk}": Coalesce(
                Sum(
                    "relevant_accesslogs__value",
                    filter=Q(relevant_accesslogs__platform_id=platform.pk),
                ),
                0,
            )
            for platform in self.all_platforms
        }
        annotations.update(interest_annot_params)
        annotations["total_interest"] = Coalesce(Sum("relevant_accesslogs__value"), 0)
        return annotations

    def _postprocess_paginated(self, result):
        result = super()._postprocess_paginated(result)
        for record in result:
            record.interests = {
                pl.pk: getattr(record, f"pl_{pl.pk}")
                for pl in self.all_platforms
                if pl.pk in record.platform_ids
            }
        return result

    def _postprocess(self, result):
        order_by = self.request.query_params.get("order_by")
        desc = self.request.query_params.get("desc", "true")
        if order_by:
            prefix = "-" if desc == "true" else ""
            result = result.order_by(prefix + order_by)
        # result = result.filter(**{f'pl_{platform.pk}__gt': 0 for platform in self.all_platforms})
        return result


class StartERMSSyncPlatformsTask(APIView):
    permission_classes = [SuperuserOrAdminPermission]

    def post(self, request):
        task = erms_sync_platforms_task.delay()
        return Response({"id": task.id})


class TitleOverlapBatchViewSet(ModelViewSet):
    serializer_class = TitleOverlapBatchSerializer
    # do not allow put or patch
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        return TitleOverlapBatch.objects.filter(last_updated_by=self.request.user).select_related(
            "organization"
        )

    @action(detail=True, methods=["post"])
    def process(self, request, pk=None):
        batch = self.get_object()
        batch.state = TitleOverlapBatchState.PROCESSING
        batch.save()
        url_base = build_absolute_uri(self.request, "/")
        task = process_title_overlap_batch_task.delay(batch.pk, url_base)

        return Response(
            {
                "task_id": task.id,
                "batch": self.serializer_class(batch, context={"request": request}).data,
            },
            status=HTTP_202_ACCEPTED,
        )

    def get_serializer_class(self):
        if self.action == "create":
            return TitleOverlapBatchCreateSerializer
        return super().get_serializer_class()


class OrganizationAltNameViewSet(CreateModelMixin, DestroyModelMixin, GenericViewSet):
    permission_classes = [SuperuserOrAdminPermission]

    serializer_class = OrganizationAltNameSerializer

    def get_queryset(self):
        organization = get_object_or_404(Organization, pk=self.kwargs["organization_pk"])
        return organization.organizationaltname_set

    @transaction.atomic
    def perform_create(self, serializer):
        organization = get_object_or_404(Organization, pk=self.kwargs["organization_pk"])
        try:
            OrganizationAltName.objects.create(
                name=serializer.validated_data["name"], organization=organization
            )
        except DjangoValidationError as e:
            # Rewrap django exception (used in django admin) to drf exception (API)
            raise ValidationError(e.message_dict) from None


class ItemViewSet(ReadOnlyModelViewSet):
    serializer_class = ItemSerializer
    filter_backends = [SearchFilter, PkMultiValueFilterBackend, OrderByFilter, PubTypeFilter]
    search_fields = ["name", "doi", "issn", "eissn", "isbn", "authors__name"]
    pagination_class = StandardResultsSetPagination

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.interest_rt = ReportType.objects.get_interest_rt()
        self.interest_metrics = get_interest_metrics()
        self.organization_id = None
        self.platform_id = None
        self.title_id = None
        self.filters_ = {}

    @property
    def add_interest(self):
        return to_bool(self.request.query_params.get("interest"))

    @property
    def add_parent_titles(self):
        return to_bool(self.request.query_params.get("parent_titles"))

    def get_queryset(self):
        self.organization_id = self.kwargs.get("organization_pk")
        self.platform_id = self.kwargs.get("platform_pk")
        self.title_id = self.kwargs.get("title_pk")
        fltrs = {}

        # interest config and organization filter
        ic = InterestConfig.objects.default()
        org_filter = {}
        if self.organization_id:
            # clickhouse=True will use oranization_id instead of organization__pk
            # which is completely compatible with both Django and ClickHouse in this case
            # (it is used only in AccessLog query)
            org_filter = organization_filter_from_org_id(
                self.organization_id, self.request.user, clickhouse=True
            )
            fltrs.update(org_filter)

        if self.platform_id:
            fltrs["platform_id"] = self.platform_id
        if self.title_id:
            fltrs["target_id"] = self.title_id
        if date_from := self.request.query_params.get("start"):
            fltrs["date__gte"] = parse_month(date_from)
        if date_to := self.request.query_params.get("end"):
            fltrs["date__lte"] = parse_month(date_to)
        qs = Item.objects.all().prefetch_related("authors")
        if fltrs:
            # until we have something equivalent to PlatformTitle for Items, this is the best we
            # can do. It will be good enough until there are many item-related records in AccessLog
            item_ids = (
                AccessLog.objects.exclude(item_id__isnull=True)
                .filter(**fltrs)
                .values_list("item_id", flat=True)
            )
            qs = qs.filter(pk__in=item_ids)
            self.filters_ = fltrs

        # add interest annotations
        if self.add_interest:
            # only when interest is explicitly requested, we add interest annotations
            accesslog_filter = extend_query_filter(fltrs, "accesslog__")
            accesslog_filter["accesslog__report_type_id"] = self.interest_rt.pk
            # add interest config filters
            ic = InterestConfig.objects.default()
            if org_filter:  # if the filter is not empty, it means that the organization id is valid
                org = Organization.objects.get(pk=self.organization_id)
                ic = org.get_interest_config()
            interest_filters, negated_interest_filters = ic.get_interest_filters()
            accesslog_filter.update(extend_query_filter(interest_filters, "accesslog__"))
            negated_interest_filters = extend_query_filter(negated_interest_filters, "accesslog__")

            condition = Q(**accesslog_filter)
            if negated_interest_filters:
                condition &= ~Q(**negated_interest_filters)
            qs = qs.annotate(relevant_accesslogs=FilteredRelation("accesslog", condition=condition))
            interest_annot_params = {
                im.short_name: Coalesce(
                    Sum("relevant_accesslogs__value", filter=Q(relevant_accesslogs__metric=im)), 0
                )
                for im in self.interest_metrics
            }
            qs = qs.annotate(**interest_annot_params)
        return qs

    def _postprocess_record(self, record):
        if self.add_interest:
            record.interests = {
                im.short_name: getattr(record, im.short_name) for im in self.interest_metrics
            }
        return record

    def _map_item_ids_to_title_ids(
        self, item_ids: typing.List[int]
    ) -> typing.Dict[int, typing.List[int]]:
        """
        Find all titles that are associated with the given list of item ids.
        It uses the AccessLog model with filters applied to the query matching the `filters_`
        attribute used in the ItemViewSet.

        When available, it uses ClickHouse to get the title ids.
        """
        if self.request.USE_CLICKHOUSE:
            qs = (
                AccessLogCube.query()
                .filter(item_id__in=item_ids, **self.filters_)
                .group_by("item_id")
                .aggregate(title_ids=HArrayAgg(distinct="target_id"))
            )
            return {
                rec.item_id: [title_id for title_id in rec.title_ids if title_id]
                for rec in ch_backend.get_records(qs)
            }
        else:
            qs = (
                AccessLog.objects.filter(item_id__in=item_ids, **self.filters_)
                .values("item_id")
                .annotate(title_ids=ArrayAgg("target_id", distinct=True))
            )
            return {
                rec["item_id"]: [title_id for title_id in rec["title_ids"] if title_id]
                for rec in qs
            }

    def _map_item_ids_to_titles(
        self, item_ids: typing.List[int]
    ) -> typing.Dict[int, typing.List[Title]]:
        item_id_to_title_ids = self._map_item_ids_to_title_ids(item_ids)
        title_ids = set(chain.from_iterable(item_id_to_title_ids.values()))
        title_ids_to_titles = Title.objects.filter(pk__in=title_ids).in_bulk()
        return {
            item_id: [title_ids_to_titles[title_id] for title_id in item_id_to_title_ids[item_id]]
            for item_id in item_ids
        }

    def paginate_queryset(self, queryset):
        qs = super().paginate_queryset(queryset)
        for record in qs:
            self._postprocess_record(record)
        if self.add_parent_titles:
            item_id_to_titles = self._map_item_ids_to_titles([record.pk for record in qs])
            for record in qs:
                record.parent_titles = item_id_to_titles[record.pk]
        return qs

    def get_object(self):
        ret = super().get_object()
        self._postprocess_record(ret)
        if self.add_parent_titles:
            item_id_to_titles = self._map_item_ids_to_titles([ret.pk])
            ret.parent_titles = item_id_to_titles[ret.pk]
        return ret
