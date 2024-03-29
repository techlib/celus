from allauth.utils import build_absolute_uri
from api.auth import extract_org_from_request_api_key
from api.permissions import HasOrganizationAPIKey
from charts.models import ReportDataView
from charts.serializers import ReportDataViewSerializer
from core.exceptions import BadRequestException
from core.filters import PkMultiValueFilterBackend
from core.logic.dates import date_filter_from_params
from core.pagination import SmartPageNumberPagination
from core.permissions import SuperuserOrAdminPermission, ViewPlatformPermission
from django.conf import settings
from django.contrib.postgres.aggregates import ArrayAgg
from django.db import transaction
from django.db.models import Count, Exists, FilteredRelation, OuterRef, Prefetch, Q, Sum
from django.db.models.functions import Coalesce
from hcube.api.models.aggregation import Count as CubeCount
from logs.cubes import AccessLogCube, ch_backend
from logs.logic.queries import replace_report_type_with_materialized
from logs.models import (
    AccessLog,
    DimensionText,
    ImportBatch,
    InterestGroup,
    ReportInterestMetric,
    ReportType,
)
from logs.serializers import PlatformInterestReportSerializer, ReportTypeExtendedSerializer
from logs.views import StandardResultsSetPagination
from nibbler.models import ParserDefinition
from organizations.logic.queries import extend_query_filter, organization_filter_from_org_id
from organizations.models import Organization
from pandas import DataFrame
from publications.models import (
    Platform,
    PlatformTitle,
    Title,
    TitleOverlapBatch,
    TitleOverlapBatchState,
)
from publications.serializers import (
    DeleteAllDataPlatformSerializer,
    SimplePlatformSerializer,
    TitleCountSerializer,
    TitleOverlapBatchCreateSerializer,
    TitleOverlapBatchSerializer,
    UseCaseSerializer,
)
from recache.util import recache_queryset
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_202_ACCEPTED
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet, ViewSet
from tags.models import Tag

from .filters import PlatformFilter
from .logic.use_cases import get_use_cases
from .serializers import (
    AllPlatformSerializer,
    DetailedPlatformSerializer,
    PlatformSerializer,
    TitleSerializer,
)
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
            raise ValidationError(detail=f'Bad value for the "organization_pk" param: "{str(exc)}"')
        if organization_pk and organization_pk != -1:
            return Organization.objects.get(pk=organization_pk)
        else:
            # all organizations were requested using -1
            return None

    def get_queryset(self):
        """Returns Platforms which can be displayed to the user"""
        organization = self._organization_pk_to_obj(self.kwargs.get('organization_pk'))

        return (
            self.request.user.accessible_platforms(organization=organization)
            .select_related('source', 'source__organization')
            .order_by('name')
            .annotate(
                has_raw_parser=Exists(
                    ParserDefinition.objects.filter(
                        source_id=OuterRef('source_id'),
                        platforms__contains=[OuterRef('short_name')],
                    )
                )
            )
        )

    @action(detail=False, url_path='use-cases', serializer_class=UseCaseSerializer)
    def use_cases(self, request, organization_pk):
        """Returns data how are the platforms successfully used"""
        platforms = self.get_queryset()
        use_cases = get_use_cases(platforms)
        serializer = UseCaseSerializer(data=list(use_cases), many=True)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)

    @action(detail=True, url_path='report-types')
    def get_report_types(self, request, pk, organization_pk):
        """
        Provides a list of report types associated with this platform + list of all COUNTER reports.
        This view represents all the reports that may be manually uploaded to a platform.
        """
        organization = self._organization_pk_to_obj(organization_pk)
        platform = get_object_or_404(
            request.user.accessible_platforms(organization=organization), pk=pk
        )
        report_types = (
            ReportType.objects.filter(
                Q(interest_platforms=platform)
                | Q(counterreporttype__isnull=False, source__isnull=True)
            )
            .distinct()
            .select_related("counterreporttype")
            .prefetch_related(
                'reportinterestmetric_set__metric',
                'reportinterestmetric_set__interest_group',
                'source',
                'source__organization',
                'controlled_metrics',
            )
        )
        if not settings.ALLOW_NONCOUNTER_DATA:
            report_types = report_types.filter(counterreporttype__isnull=False)
        return Response(ReportTypeExtendedSerializer(report_types, many=True).data)


class PlatformViewSet(CreateModelMixin, UpdateModelMixin, ReadOnlyModelViewSet):

    serializer_class = PlatformSerializer

    def get_permissions(self):
        permission_classes = list(self.permission_classes)

        def generate_permission(organization_id: int):
            # Create admin permission for given organization
            class Permission(IsAuthenticated):
                def has_permission(self, request, *args, **kwargs):
                    if not settings.ALLOW_USER_CREATED_PLATFORMS:
                        return False
                    return request.user.has_organization_admin_permission(int(organization_id))

            return Permission

        if self.action in ['create', 'delete_all_data']:
            organization_id = self.kwargs['organization_pk']
            Permission = generate_permission(organization_id)
            permission_classes = [e & Permission for e in permission_classes]
        elif self.action in ['update', 'partial_update']:
            obj = get_object_or_404(Platform, pk=self.kwargs['pk'])
            if obj.source and obj.source.organization:
                Permission = generate_permission(obj.source.organization.pk)
                permission_classes = [e & Permission for e in permission_classes]
            else:
                # disallow updating platform without organization
                class Permission:
                    def has_permission(self, *args, **kwargs):
                        return False

                permission_classes = [Permission]

        return [permission() for permission in permission_classes]

    @transaction.atomic
    def perform_create(self, serializer):
        if self.kwargs['organization_pk'] != '-1':
            organization = get_object_or_404(Organization, pk=self.kwargs['organization_pk'])
            source = organization.get_or_create_private_source()
        else:
            source = None

        serializer.is_valid()  # -> sets validated_data
        if Platform.objects.filter(
            Q(ext_id__isnull=True)
            & Q(short_name=serializer.validated_data["short_name"])
            & (Q(source__isnull=True) | Q(source=source))
        ).exists():
            raise ValidationError({"short_name": "Already exists"}, code="unique")

        platform = serializer.save(ext_id=None, source=source)
        platform.create_default_interests()

    def perform_update(self, serializer):
        serializer.save(
            ext_id=None, source=self.get_object().source
        )  # source can be selected only on create

    def get_queryset(self):
        """
        Should return only platforms for the requested organization
        """
        org_filter = organization_filter_from_org_id(
            self.kwargs.get('organization_pk'), self.request.user
        )
        if org_filter:
            qs = Platform.objects.filter(
                Q(**org_filter)
                | Q(**extend_query_filter(org_filter, 'sushicredentials__'))
                | Q(**extend_query_filter(org_filter, 'source__'))
            ).distinct()
        # only those that have an organization connected
        elif 'used_only' in self.request.query_params:
            qs = Platform.objects.filter(
                Q(organization__isnull=False)
                | Q(sushicredentials__isnull=False)
                | Q(source__organization__isnull=False)
            ).distinct()
        else:
            qs = Platform.objects.all()
        return qs.select_related('source', 'source__organization')

    @action(methods=['GET'], url_path='no-interest-defined', detail=False)
    def without_interest_definition(self, request, organization_pk):
        org_filter = organization_filter_from_org_id(organization_pk, request.user)
        import_batch_query = ImportBatch.objects.filter(platform_id=OuterRef('pk'))
        qs = Platform.objects.filter(**org_filter, interest_reports__isnull=True).annotate(
            has_data=Exists(import_batch_query)
        )
        return Response(DetailedPlatformSerializer(qs, many=True).data)

    @action(methods=['GET'], url_path='title-count', url_name='title-count', detail=False)
    def title_count(self, request, organization_pk):
        date_filter_params = date_filter_from_params(request.GET)
        if request.USE_CLICKHOUSE:
            from logs.cubes import AccessLogCube, ch_backend

            org_filter = organization_filter_from_org_id(
                organization_pk, request.user, clickhouse=True
            )
            query = (
                AccessLogCube.query()
                .filter(**org_filter, **date_filter_params)
                .group_by('platform_id')
                .order_by('platform_id')
                .filter(target_id__not_in=[0])
                .aggregate(title_count=CubeCount(distinct='target_id'))
            )
            return Response(
                {'platform': rec.platform_id, 'title_count': rec.title_count}
                for rec in ch_backend.get_records(query, auto_use_materialized_views=True)
            )
        else:
            org_filter = organization_filter_from_org_id(organization_pk, request.user)
            qs = (
                PlatformTitle.objects.filter(**org_filter, **date_filter_params)
                .values('platform')
                .annotate(title_count=Count('title', distinct=True))
            )
            return Response(qs)

    @action(methods=['GET'], url_path='title-count', url_name='title-count', detail=True)
    def title_count_detail(self, request, organization_pk, pk):
        org_filter = organization_filter_from_org_id(organization_pk, request.user)
        date_filter_params = date_filter_from_params(request.GET)
        qs = (
            PlatformTitle.objects.filter(platform_id=pk, **org_filter, **date_filter_params)
            .values('platform')
            .annotate(title_count=Count('title', distinct=True))
        )
        try:
            result = qs.get()
            title_count = result.get('title_count', 0)
        except PlatformTitle.DoesNotExist:
            title_count = 0
        return Response({'title_count': title_count})

    @action(methods=['GET'], url_path='title-ids-list', url_name='title-ids-list', detail=False)
    def title_id_list(self, request, organization_pk):
        org_filter = organization_filter_from_org_id(organization_pk, request.user)
        date_filter_params = date_filter_from_params(request.GET)
        pub_type_arg = self.request.query_params.get('pub_type')
        search_filters = []
        if pub_type_arg:
            search_filters.append(Q(title__pub_type__in=pub_type_arg.split(',')))
        qs = (
            PlatformTitle.objects.filter(*search_filters, **org_filter, **date_filter_params)
            .values_list('platform_id', 'title_id')
            .distinct()
        )
        result = {}
        for platform_id, title_id in qs:
            if platform_id not in result:
                result[platform_id] = []
            result[platform_id].append(title_id)
        return Response(result)

    @action(methods=['POST'], url_path='delete-all-data', url_name='delete-all-data', detail=True)
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
                    f' #{organization_pk}'
                )

        task = delete_platform_data_task.delay(pk, org_ids, delete_platform)
        return Response({'success': True, 'task_id': task.id})


class PlatformInterestViewSet(ViewSet):
    @classmethod
    def get_report_type_and_filters(cls):
        interest_rt = ReportType.objects.get_interest_rt()
        # parameters for annotation defining an annotation for each of the interest groups
        interest_type_dim = interest_rt.dimensions_sorted[0]
        # we get active InterestGroups in order to filter out unused InterestGroups
        # for which the dimension text mapping still exists
        ig_names = {x['short_name'] for x in InterestGroup.objects.all().values('short_name')}
        interest_annot_params = {
            interest_type.text: Coalesce(Sum('value', filter=Q(dim1=interest_type.pk)), 0)
            for interest_type in interest_type_dim.dimensiontext_set.filter(text__in=ig_names)
        }
        return interest_rt, interest_annot_params

    def get_queryset(self, request, organization_pk):
        org_filter = organization_filter_from_org_id(organization_pk, request.user)
        date_filter_params = date_filter_from_params(request.GET)
        interest_rt, interest_annot_params = self.get_report_type_and_filters()
        accesslog_filter = {'report_type': interest_rt, **org_filter, **date_filter_params}
        replace_report_type_with_materialized(accesslog_filter)
        result = (
            AccessLog.objects.filter(**accesslog_filter)
            .values('platform')
            .annotate(**interest_annot_params)
        )
        return result

    def list(self, request, organization_pk):
        qs = self.get_queryset(request, organization_pk)
        data_format = request.GET.get('format')
        if data_format in ('csv', 'xlsx'):
            # when exporting, we want to rename the columns and rows
            data = DataFrame(qs)
            platform_names = {
                pl['pk']: pl['short_name']
                for pl in Platform.objects.all().values('pk', 'short_name')
            }
            metric_names = {
                m['short_name']: m['name']
                for m in InterestGroup.objects.all().values('short_name', 'name')
            }
            if 'platform' in data:
                data['platform'] = [platform_names[pk] for pk in data['platform']]
                data.set_index('platform', drop=True, inplace=True)
                data.rename(columns=metric_names, inplace=True)
            return Response(
                data,
                headers={'Content-Disposition': f'attachment; filename="export.{data_format}"'},
            )
        return Response(qs)

    def retrieve(self, request, organization_pk, pk):
        qs = self.get_queryset(request, organization_pk)
        data = qs.filter(platform_id=pk)
        if data:
            return Response(data[0])
        return Response({})

    @action(detail=True, url_path='by-year')
    def by_year(self, request, pk, organization_pk):
        interest_rt, interest_annot_params = self.get_report_type_and_filters()
        org_filter = organization_filter_from_org_id(organization_pk, request.user)
        accesslog_filter = {'report_type': interest_rt, 'platform_id': pk, **org_filter}
        replace_report_type_with_materialized(accesslog_filter)
        result = (
            AccessLog.objects.filter(**accesslog_filter)
            .values('date__year')
            .annotate(**interest_annot_params)
        )
        return Response(result)

    @action(detail=False, url_path='by-year')
    def list_by_year(self, request, organization_pk):
        interest_rt, interest_annot_params = self.get_report_type_and_filters()
        org_filter = organization_filter_from_org_id(organization_pk, request.user)
        accesslog_filter = {'report_type': interest_rt, **org_filter}
        replace_report_type_with_materialized(accesslog_filter)
        result = (
            AccessLog.objects.filter(**accesslog_filter)
            .values('platform', 'date__year')
            .annotate(**interest_annot_params)
        )
        return Response(result)


class PlatformInterestReportViewSet(ReadOnlyModelViewSet):
    serializer_class = PlatformInterestReportSerializer
    queryset = Platform.objects.prefetch_related(
        "interest_reports",
        Prefetch(
            "interest_reports__reportinterestmetric_set",
            queryset=ReportInterestMetric.objects.select_related(
                "metric", "target_metric", "interest_group"
            ),
        ),
    )


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
                    'cannot access the view without api key or session based authentication'
                )
        else:
            qs = qs.filter(pk__in=self.request.user.accessible_platforms())
        return qs.order_by('name')


class GlobalTitleViewSet(ReadOnlyModelViewSet):

    serializer_class = TitleSerializer
    queryset = Title.objects.all()
    pagination_class = StandardResultsSetPagination
    filter_backends = [PkMultiValueFilterBackend]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.order_by('name')


class BaseTitleViewSet(ReadOnlyModelViewSet):

    serializer_class = TitleSerializer
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

    def _extra_accesslog_filters(self):
        return {}

    def _annotations(self):
        return {}

    def _postprocess(self, result):
        return result

    def _postprocess_paginated(self, result):
        if not result:
            return result
        # the stored .title_selection_query contains annotation with platform_count and
        # platform_ids
        # here we use it to add this information to the title objects after pagination
        result_title_ids = [title.pk for title in result]
        title_info = {
            record['pk']: record
            for record in self.title_selection_query.filter(pk__in=result_title_ids).values(
                'pk', 'platform_count', 'platform_ids'
            )
        }
        for record in result:
            record.platform_count = title_info[record.pk]['platform_count']
            record.platform_ids = title_info[record.pk]['platform_ids']
        return result

    def _before_queryset(self):
        pass

    def get_queryset(self):
        """
        Should return only titles for specific organization and platform
        """
        self.org_filter = organization_filter_from_org_id(
            self.kwargs.get('organization_pk'), self.request.user
        )
        self.date_filter = date_filter_from_params(self.request.GET)
        # run stuff before we start creating the queryset
        self._before_queryset()
        # put together filters for title itself
        search_filters = []
        q = self.request.query_params.get('q')
        if q:
            search_filters = [
                Q(name__ilike=p)
                | Q(isbn__ilike=p)
                | Q(eissn__ilike=p)
                | Q(issn__ilike=p)
                | Q(doi__ilike=p)
                for p in q.split()
            ]
        pub_type_arg = self.request.query_params.get('pub_type')
        if pub_type_arg:
            search_filters.append(Q(pub_type=pub_type_arg))
        # tags

        # tags
        if tag_arg := self.request.query_params.get('tags'):
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
        accesslog_filter = {**self._extra_accesslog_filters()}
        title_qs = Title.objects.all()
        if accesslog_filter:
            # we have some filters for accesslog - this means we have to add the relevant
            # accesslogs to the queryset
            accesslog_filter.update(**extend_query_filter(self.date_filter, 'accesslog__'))
            title_qs = title_qs.annotate(
                relevant_accesslogs=FilteredRelation('accesslog', condition=Q(**accesslog_filter))
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
            **extend_query_filter(self.date_filter, 'platformtitle__'),
            **extend_query_filter(self.org_filter, 'platformtitle__'),
            **extra_filters,
        ).annotate(
            platform_count=Count('platformtitle__platform_id', distinct=True),
            platform_ids=ArrayAgg('platformtitle__platform_id', distinct=True),
        )
        if 'multiplatform' in self.request.query_params:
            base_title_query = base_title_query.filter(platform_count__gt=1)

        base_title_query = base_title_query.distinct().order_by()
        self.title_selection_query = base_title_query
        result = title_qs.filter(pk__in=base_title_query)
        annot = self._annotations()
        if annot:
            result = result.annotate(**annot)
        result = self._postprocess(result.order_by('name', 'pub_type'))
        return result

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)

            if self.request.GET.get('format') in ('csv', 'xlsx'):
                # for CSV and XLSX formats, we return a DataFrame and DRF takes care of the rest
                data = []
                for rec in serializer.data:
                    # inline interests
                    interest = rec.pop('interests')
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
        org_filter = organization_filter_from_org_id(
            self.kwargs.get('organization_pk'), self.request.user
        )
        date_filter = date_filter_from_params(self.request.GET)
        interest_rt = ReportType.objects.get_interest_rt()
        search_filters = []
        pub_type_arg = self.request.query_params.get('pub_type')
        if pub_type_arg:
            search_filters.append(Q(target__pub_type__in=pub_type_arg.split(',')))
        queryset = (
            AccessLog.objects.filter(
                report_type=interest_rt, *search_filters, **date_filter, **org_filter
            )
            .values('target_id')
            .exclude(target_id__isnull=True)
            .annotate(interest=Sum('value'))
        )
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        data = queryset.filter(interest__gt=0).order_by().values('target_id', 'interest')
        return Response(data)

    def retrieve(self, request, pk, *args, **kwargs):
        queryset = self.get_queryset()
        data = get_object_or_404(queryset.order_by().values('interest'), target_id=pk)
        return Response(data)


class PlatformTitleViewSet(BaseTitleViewSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.platform = None

    def _extra_filters(self):
        filters = super()._extra_filters()
        self.platform = get_object_or_404(
            Platform.objects.filter(**self.org_filter), pk=self.kwargs['platform_pk']
        )
        # filters['accesslog__platform'] = platform
        filters['platformtitle__platform'] = self.platform
        return filters


class TitleInterestMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.interest_rt = None
        self.interest_type_dim = None
        self.interest_groups_names = set()

    def _before_queryset(self):
        self.interest_rt = ReportType.objects.get_interest_rt()
        self.interest_type_dim = self.interest_rt.dimensions_sorted[0]
        self.interest_groups_names = {
            x['short_name'] for x in InterestGroup.objects.all().values('short_name')
        }

    def _extra_accesslog_filters(self):
        filters = super()._extra_accesslog_filters()
        filters['accesslog__report_type_id'] = self.interest_rt.pk
        if hasattr(self, 'platform') and self.platform:
            filters['accesslog__platform_id'] = self.platform.pk
        if self.org_filter:
            filters['accesslog__organization_id'] = self.org_filter.get('organization__pk')
        return filters

    def _annotations(self):
        annotations = super()._annotations()
        interest_annot_params = {
            interest_type.text: Coalesce(
                Sum(
                    'relevant_accesslogs__value',
                    filter=Q(relevant_accesslogs__dim1=interest_type.pk),
                ),
                0,
            )
            for interest_type in self.interest_type_dim.dimensiontext_set.filter(
                text__in=self.interest_groups_names
            )
        }
        annotations.update(interest_annot_params)
        return annotations

    def _postprocess_paginated(self, result):
        result = super()._postprocess_paginated(result)
        interest_types = {
            interest_type.text
            for interest_type in self.interest_type_dim.dimensiontext_set.filter(
                text__in=self.interest_groups_names
            )
        }
        for record in result:
            record.interests = {it: getattr(record, it) for it in interest_types}
        return result

    def _postprocess(self, result):
        order_by = self.request.query_params.get('order_by')
        if order_by == 'tags':
            raise BadRequestException('Ordering by tags is not supported')
        desc = self.request.query_params.get('desc', 'true')
        if order_by:
            prefix = '-' if desc == 'true' else ''
            result = result.order_by(prefix + order_by, prefix + 'pk')
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
            self.kwargs.get('organization_pk'), self.request.user
        )
        extra_filters = self._extra_filters(org_filter)
        if self.request.USE_CLICKHOUSE:
            org_filter = organization_filter_from_org_id(
                self.kwargs.get('organization_pk'), self.request.user, clickhouse=True
            )
            extra_filters = {k + "_id": v.pk for k, v in extra_filters.items()}
            distinct_rts = {
                rec.report_type_id
                for rec in ch_backend.get_records(
                    AccessLogCube.query()
                    .filter(**org_filter, **extra_filters)
                    .group_by('report_type_id')
                )
            }
        else:
            access_log_filter = Q(**org_filter, **extra_filters)
            distinct_rts = set(
                AccessLog.objects.filter(access_log_filter)
                .exclude(report_type__materialization_spec__isnull=False)
                .values_list('report_type_id', flat=True)
                .distinct()
            )
        report_views = list(
            ReportDataView.objects.filter(base_report_type_id__in=distinct_rts).order_by('position')
        )
        # create proxy report view for each RT that has no report view
        rts_with_view = {rv.base_report_type_id for rv in report_views}
        to_fake = distinct_rts - rts_with_view
        for i, rt in enumerate(ReportType.objects.filter(id__in=to_fake)):
            # we use the fact that most attrs are the same in report type and report view
            rt.position = len(report_views) + i
            rt.is_proxy = True
            rt.is_standard_view = True
            report_views.append(rt)
        return report_views


class TitleReportDataViewViewSet(BaseReportDataViewViewSet):
    """
    Provides a list of report types for specific title for specific organization
    """

    def _extra_filters(self, org_filter):
        title = get_object_or_404(Title.objects.all(), pk=self.kwargs['title_pk'])
        return {'target': title}


class PlatformReportDataViewViewSet(BaseReportDataViewViewSet):
    """
    Provides a list of report types for specific organization and platform
    """

    def _extra_filters(self, org_filter):
        platform = get_object_or_404(
            Platform.objects.filter(**org_filter), pk=self.kwargs['platform_pk']
        )
        return {'platform': platform}


class PlatformTitleReportDataViewViewSet(BaseReportDataViewViewSet):
    """
    Provides a list of report types for specific title for specific organization and platform
    """

    def _extra_filters(self, org_filter):
        platform = get_object_or_404(
            Platform.objects.filter(**org_filter), pk=self.kwargs['platform_pk']
        )
        title = get_object_or_404(Title.objects.all(), pk=self.kwargs['title_pk'])
        return {'target': title, 'platform': platform}


class TitleViewSet(BaseTitleViewSet):

    serializer_class = TitleSerializer

    @action(detail=True, url_path='platforms')
    def platforms(self, request, pk, organization_pk):
        title = get_object_or_404(Title.objects.all(), pk=pk)
        org_filter = organization_filter_from_org_id(organization_pk, self.request.user)
        date_filter_params = date_filter_from_params(self.request.GET, key_start='accesslog__')
        platforms = Platform.objects.filter(
            accesslog__target=title,
            **date_filter_params,
            **extend_query_filter(org_filter, 'accesslog__'),
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
        interest_type_dim = interest_rt.dimensions_sorted[0]
        interest_type_name = self.request.query_params.get('order_by', 'full_text')

        # -- title filters --
        # publication type filter
        pub_type_arg = self.request.query_params.get('pub_type')

        # -- accesslog filters --
        # filtering only interest related accesslogs
        try:
            interest_type_id = interest_type_dim.dimensiontext_set.get(text=interest_type_name).pk
        except DimensionText.DoesNotExist:
            raise BadRequestException(detail=f'Interest type "{interest_type_name}" does not exist')
        # date filter
        date_filter = date_filter_from_params(self.request.GET)

        if self.request.USE_CLICKHOUSE and not pub_type_arg:
            from hcube.api.models.aggregation import Sum as HSum
            from logs.cubes import AccessLogCube, ch_backend

            org_filter = organization_filter_from_org_id(
                self.kwargs.get('organization_pk'), self.request.user, clickhouse=True
            )
            query = (
                AccessLogCube.query()
                .filter(report_type_id=interest_rt.pk, dim1=interest_type_id, target_id__not_in=[0])
                .group_by('target_id')
                .aggregate(**{interest_type_name: HSum('value')})
                .order_by(f"-{interest_type_name}")
            )
            if org_filter:
                query.filter(**org_filter)
            if date_filter:
                query.filter(**date_filter)
            if pub_type_arg:
                raise ValueError('pub_type filter not supported in CH yet')
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
            org_filter = organization_filter_from_org_id(
                self.kwargs.get('organization_pk'), self.request.user
            )
            interest_annot_params = {interest_type_name: Coalesce(Sum('accesslog__value'), 0)}
            filters['accesslog__report_type_id'] = interest_rt.pk
            filters['accesslog__dim1'] = interest_type_id
            if org_filter:
                filters['accesslog__organization_id'] = org_filter.get('organization__pk')
            if pub_type_arg:
                if self.request.USE_CLICKHOUSE:
                    print('`pub_type` filter not supported in ClickHouse yet.')
                filters['pub_type'] = pub_type_arg
            # date filter
            date_filter = extend_query_filter(date_filter, 'accesslog__')

            records = (
                Title.objects.all()
                .filter(**date_filter, **filters)
                .annotate(**interest_annot_params)
                .order_by(f'-{interest_type_name}')
            )[:10]
            # we recache the final queryset so that the results are automatically re-evaluated in
            # the background when needed
            records = recache_queryset(records, origin=f'top-10-titles-{interest_type_name}')
            for record in records:
                record.interests = {interest_type_name: getattr(record, interest_type_name)}
            return records


class InterestByPlatformMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.interest_rt = None
        self.all_platforms = Platform.objects.all()

    def _before_queryset(self):
        self.interest_rt = ReportType.objects.get_interest_rt()

    def _extra_accesslog_filters(self):
        filters = super()._extra_accesslog_filters()
        filters['accesslog__report_type_id'] = self.interest_rt.pk
        if self.org_filter:
            filters['accesslog__organization_id'] = self.org_filter.get('organization__pk')
        return filters

    def _annotations(self):
        annotations = super()._annotations()
        interest_annot_params = {
            f'pl_{platform.pk}': Coalesce(
                Sum(
                    'relevant_accesslogs__value',
                    filter=Q(relevant_accesslogs__platform_id=platform.pk),
                ),
                0,
            )
            for platform in self.all_platforms
        }
        annotations.update(interest_annot_params)
        annotations['total_interest'] = Coalesce(Sum('relevant_accesslogs__value'), 0)
        annotations['nonzero_platform_count'] = Count(
            'relevant_accesslogs__platform', distinct=True
        )
        return annotations

    def _postprocess_paginated(self, result):
        result = super()._postprocess_paginated(result)
        for record in result:
            record.interests = {
                pl.short_name: getattr(record, f'pl_{pl.pk}')
                for pl in self.all_platforms
                if pl.pk in record.platform_ids
            }
        return result

    def _postprocess(self, result):
        order_by = self.request.query_params.get('order_by')
        desc = self.request.query_params.get('desc', 'true')
        if order_by:
            prefix = '-' if desc == 'true' else ''
            result = result.order_by(prefix + order_by)
        # result = result.filter(**{f'pl_{platform.pk}__gt': 0 for platform in self.all_platforms})
        return result


class TitleInterestByPlatformViewSet(InterestByPlatformMixin, BaseTitleViewSet):
    """
    View for all titles with interest summed up by platform
    """

    serializer_class = TitleCountSerializer
    pagination_class = SmartResultsSetPagination


class StartERMSSyncPlatformsTask(APIView):

    permission_classes = [SuperuserOrAdminPermission]

    def post(self, request):
        task = erms_sync_platforms_task.delay()
        return Response({'id': task.id})


class TitleOverlapBatchViewSet(ModelViewSet):

    serializer_class = TitleOverlapBatchSerializer
    # do not allow put or patch
    http_method_names = ['get', 'post', 'delete']

    def get_queryset(self):
        return TitleOverlapBatch.objects.filter(last_updated_by=self.request.user).select_related(
            'organization'
        )

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        batch = self.get_object()
        batch.state = TitleOverlapBatchState.PROCESSING
        batch.save()
        url_base = build_absolute_uri(self.request, '/')
        task = process_title_overlap_batch_task.delay(batch.pk, url_base)

        return Response(
            {
                'task_id': task.id,
                'batch': self.serializer_class(batch, context={"request": request}).data,
            },
            status=HTTP_202_ACCEPTED,
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return TitleOverlapBatchCreateSerializer
        return super().get_serializer_class()
