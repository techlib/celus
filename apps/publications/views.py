from django.db import transaction
from django.db.models import Count, Sum, Q, OuterRef, Exists, FilteredRelation
from django.db.models.functions import Coalesce
from django.conf import settings

from pandas import DataFrame
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import CreateModelMixin
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet, ViewSet
from rest_framework.permissions import IsAuthenticated

from charts.models import ReportDataView
from charts.serializers import ReportDataViewSerializer
from core.exceptions import BadRequestException
from core.logic.dates import date_filter_from_params
from core.pagination import SmartPageNumberPagination
from core.permissions import (
    SuperuserOrAdminPermission,
    ViewPlatformPermission,
)
from core.models import DataSource
from logs.logic.queries import (
    extract_interests_from_objects,
    interest_annotation_params,
    replace_report_type_with_materialized,
)
from logs.models import ReportType, AccessLog, InterestGroup, ImportBatch, DimensionText
from logs.serializers import ReportTypeExtendedSerializer
from logs.views import StandardResultsSetPagination
from organizations.logic.queries import organization_filter_from_org_id, extend_query_filter
from organizations.models import Organization
from publications.models import Platform, Title, PlatformTitle
from publications.serializers import TitleCountSerializer
from recache.util import recache_queryset
from .serializers import (
    PlatformSerializer,
    DetailedPlatformSerializer,
    TitleSerializer,
    PlatformKnowledgebaseSerializer,
)
from .tasks import erms_sync_platforms_task


class SmartResultsSetPagination(StandardResultsSetPagination, SmartPageNumberPagination):
    pass


class AllPlatformsViewSet(ReadOnlyModelViewSet):
    permission_classes = [ViewPlatformPermission]

    serializer_class = PlatformSerializer

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
        return self.request.user.accessible_platforms(organization=organization).order_by('name')

    @action(detail=True, url_path='report-types')
    def get_report_types(self, request, pk, organization_pk):
        """
        Provides a list of report types associated with this platform
        """
        organization = self._organization_pk_to_obj(organization_pk)
        platform = get_object_or_404(
            request.user.accessible_platforms(organization=organization), pk=pk
        )
        report_types = ReportType.objects.filter(interest_platforms=platform).prefetch_related(
            'reportinterestmetric_set__metric', 'reportinterestmetric_set__interest_group'
        )
        # for rt in report_types:
        #     rt.used_metrics = Metric.objects.\
        #         filter(pk__in=AccessLog.objects.filter(report_type=rt, platform=platform).
        #                values('metric').distinct())
        return Response(ReportTypeExtendedSerializer(report_types, many=True).data)

    @action(detail=True, url_path='knowledgebase')
    def knowledgebase(self, request, pk, organization_pk):
        """ Get knowledgebase information about the platform """
        organization = self._organization_pk_to_obj(organization_pk)
        platform = get_object_or_404(
            request.user.accessible_platforms(organization=organization), pk=pk
        )
        return Response(PlatformKnowledgebaseSerializer(platform).data)


class PlatformViewSet(ReadOnlyModelViewSet, CreateModelMixin):

    serializer_class = PlatformSerializer

    def get_permissions(self):
        permission_classes = list(self.permission_classes)

        if self.action == 'create':
            organization_id = self.kwargs['organization_pk']

            # Create admin permission for given organization

            class PlatformCreatePermission(IsAuthenticated):
                def has_permission(self, request, *args, **kwargs):
                    if not settings.ALLOW_USER_CREATED_PLATFORMS:
                        return False
                    return request.user.has_organization_admin_permission(int(organization_id))

            permission_classes = [e & PlatformCreatePermission for e in permission_classes]

        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        # get the soruce of the organization
        organization_id = self.kwargs['organization_pk']
        try:
            source = DataSource.objects.get(
                organization_id=organization_id, type=DataSource.TYPE_ORGANIZATION
            )
        except DataSource.DoesNotExist:
            raise NotFound({"msg": f"no data source found for organization {organization_id}"})

        with transaction.atomic():
            platform = serializer.save(ext_id=None, source=source)

    def get_queryset(self):
        """
        Should return only platforms for the requested organization
        """
        org_filter = organization_filter_from_org_id(
            self.kwargs.get('organization_pk'), self.request.user
        )
        return Platform.objects.filter(**org_filter)

    @action(methods=['GET'], url_path='no-interest-defined', detail=False)
    def without_interest_definition(self, request, organization_pk):
        org_filter = organization_filter_from_org_id(organization_pk, request.user)
        import_batch_query = ImportBatch.objects.filter(platform_id=OuterRef('pk'))
        qs = Platform.objects.filter(**org_filter, interest_reports__isnull=True).annotate(
            has_data=Exists(import_batch_query)
        )
        return Response(DetailedPlatformSerializer(qs, many=True).data)

    @action(methods=['GET'], url_path='title-count', detail=False)
    def title_count(self, request, organization_pk):
        org_filter = organization_filter_from_org_id(organization_pk, request.user)
        date_filter_params = date_filter_from_params(request.GET)
        qs = (
            PlatformTitle.objects.filter(**org_filter, **date_filter_params)
            .values('platform')
            .annotate(title_count=Count('title', distinct=True))
        )
        return Response(qs)

    @action(methods=['GET'], url_path='title-count', detail=True)
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


class DetailedPlatformViewSet(ReadOnlyModelViewSet):

    serializer_class = DetailedPlatformSerializer

    def get_queryset(self):
        """
        Should return only platforms for the requested organization.
        Should include title_count which counts titles on the platform
        """
        try:
            interest_rt = ReportType.objects.get(short_name='interest', source__isnull=True)
        except ReportType.DoesNotExist:
            raise ValueError('No interest report type exists')
        org_filter = organization_filter_from_org_id(
            self.kwargs.get('organization_pk'), self.request.user
        )
        # filters for the suitable access logs
        count_filter = extend_query_filter(org_filter, 'accesslog__')
        # we prefilter using the same filter as for count annotation
        # but without the interest_group filter
        prefilter = dict(count_filter)
        # parameters for annotation defining an annotation for each of the interest groups
        interest_annot_params = interest_annotation_params(count_filter, interest_rt)
        # add more filters for dates
        date_filter_params = date_filter_from_params(self.request.GET, key_start='accesslog__')
        if date_filter_params:
            count_filter.update(date_filter_params)
            prefilter.update(date_filter_params)

        # the following creates the interest dict attr from the interest annotations
        if self.lookup_field not in self.kwargs:
            # we are not filtering by id, so we are getting a list and thus adding interest here
            # otherwise we will do it in get_object
            # also we filter only platforms that have some data for the organization at hand
            result = (
                Platform.objects.filter(**org_filter)
                .filter(**prefilter)
                .annotate(
                    title_count=Count('accesslog__target', distinct=True, filter=Q(**count_filter)),
                    **interest_annot_params,
                )
            )
            extract_interests_from_objects(interest_rt, result)
        else:
            # we are filtering by ID and thus getting only one object
            # in this case we drop the prefilter so that it is possible to get data
            # for platforms that are not connected to the organization
            result = Platform.objects.filter(**org_filter).annotate(
                title_count=Count('accesslog__target', distinct=True, filter=Q(**count_filter)),
                **interest_annot_params,
            )
        return result

    def get_object(self):
        # we need to enrich the result here as the interests added in get_queryset would not
        # survive the filtering done super().get_object()
        obj = super().get_object()
        interest_rt = ReportType.objects.get(short_name='interest', source__isnull=True)
        extract_interests_from_objects(interest_rt, [obj])
        return obj


class PlatformInterestViewSet(ViewSet):
    @classmethod
    def get_report_type_and_filters(cls):
        interest_rt = ReportType.objects.get(short_name='interest', source__isnull=True)
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
        """
        Provides a list of report types associated with this platform
        """
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
        """
        Provides a list of report types associated with this platform
        """
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


class BaseTitleViewSet(ReadOnlyModelViewSet):

    serializer_class = TitleSerializer
    # pagination_class = StandardResultsSetPagination

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.org_filter = None
        self.date_filter = None

    def _extra_filters(self):
        return {}

    def _extra_accesslog_filters(self):
        return {}

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
                Q(name__ilike=p) | Q(isbn__ilike=p) | Q(issn__ilike=p) | Q(doi__ilike=p)
                for p in q.split()
            ]
        pub_type_arg = self.request.query_params.get('pub_type')
        if pub_type_arg:
            search_filters.append(Q(pub_type=pub_type_arg))
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
        )
        if 'multiplatform' in self.request.query_params:
            base_title_query = base_title_query.annotate(
                platform_count=Count('platformtitle__platform_id', distinct=True)
            ).filter(platform_count__gt=1)

        base_title_query = base_title_query.distinct()
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
        self.interest_rt = ReportType.objects.get(short_name='interest', source__isnull=True)
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
        desc = self.request.query_params.get('desc', 'true')
        if order_by:
            prefix = '-' if desc == 'true' else ''
            result = result.order_by(prefix + order_by)
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
        access_log_filter = Q(**org_filter, **extra_filters)
        distinct_rts = (
            AccessLog.objects.filter(access_log_filter).values('report_type_id').distinct()
        )
        report_types = ReportDataView.objects.filter(base_report_type_id__in=distinct_rts).order_by(
            'position'
        )
        # the following is a alternative approach which uses Exists subquery
        # it might be faster in some cases but seems to be somewhat slower in others
        # access_log_query = AccessLog.objects.\
        #     filter(access_log_filter,
        #            report_type_id=OuterRef('base_report_type_id')).values('pk')
        # report_types = ReportDataView.objects.annotate(has_al=Exists(access_log_query)).\
        #     filter(has_al=True)
        if self.more_precise_results:
            return report_types
            # the following is commented out as it is not clear if it is still required
            # after a change in the query that gets the report_types
            # report_types_clean = []
            # for rt in report_types:
            #     if rt.logdata_qs().filter(**org_filter, **extra_filters).exists():
            #         report_types_clean.append(rt)
            # return report_types_clean
        else:
            return report_types


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
    View for all titles for selected organization
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
        interest_rt = ReportType.objects.get(short_name='interest', source__isnull=True)
        interest_type_dim = interest_rt.dimensions_sorted[0]
        interest_type_name = self.request.query_params.get('order_by', 'full_text')

        filters = {}
        # -- title filters --
        # publication type filter
        pub_type_arg = self.request.query_params.get('pub_type')
        if pub_type_arg:
            filters['pub_type'] = pub_type_arg

        # -- accesslog filters --
        # filtering only interest related accesslogs
        try:
            interest_type_id = interest_type_dim.dimensiontext_set.get(text=interest_type_name).pk
        except DimensionText.DoesNotExist:
            raise BadRequestException(detail=f'Interest type "{interest_type_name}" does not exist')
        filters['accesslog__report_type_id'] = interest_rt.pk
        filters['accesslog__dim1'] = interest_type_id
        # organization filter
        org_filter = organization_filter_from_org_id(
            self.kwargs.get('organization_pk'), self.request.user
        )
        if org_filter:
            filters['accesslog__organization_id'] = org_filter.get('organization__pk')
        # date filter
        date_filter = extend_query_filter(date_filter_from_params(self.request.GET), 'accesslog__')

        interest_annot_params = {interest_type_name: Coalesce(Sum('accesslog__value'), 0)}

        records = (
            Title.objects.all()
            .filter(**date_filter, **filters)
            .annotate(**interest_annot_params)
            .order_by(f'-{interest_type_name}')
        )[:10]
        # we recache the final queryset so that the results are automatically re-evaluated in the
        # background when needed
        records = recache_queryset(records, origin=f'top-10-titles-{interest_type_name}')

        for record in records:
            record.interests = {interest_type_name: getattr(record, interest_type_name)}
        return records


class StartERMSSyncPlatformsTask(APIView):

    permission_classes = [SuperuserOrAdminPermission]

    def post(self, request):
        task = erms_sync_platforms_task.delay()
        return Response({'id': task.id,})
