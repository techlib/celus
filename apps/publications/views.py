from django.db.models import Count, Sum, Q, OuterRef, Exists, FilteredRelation
from django.db.models.functions import Coalesce
from pandas import DataFrame
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet, ViewSet

from charts.models import ReportDataView
from charts.serializers import ReportDataViewSerializer
from core.logic.dates import date_filter_from_params
from core.pagination import SmartPageNumberPagination
from core.permissions import SuperuserOrAdminPermission
from logs.logic.queries import extract_interests_from_objects, interest_annotation_params
from logs.models import ReportType, AccessLog, InterestGroup, ImportBatch, Metric
from logs.serializers import ReportTypeExtendedSerializer
from logs.views import StandardResultsSetPagination
from organizations.logic.queries import organization_filter_from_org_id, extend_query_filter
from publications.models import Platform, Title, PlatformTitle
from publications.serializers import TitleCountSerializer
from .serializers import PlatformSerializer, DetailedPlatformSerializer, TitleSerializer
from .tasks import erms_sync_platforms_task


class SmartResultsSetPagination(StandardResultsSetPagination, SmartPageNumberPagination):
    pass


class AllPlatformsViewSet(ReadOnlyModelViewSet):

    serializer_class = PlatformSerializer
    queryset = Platform.objects.all().order_by('name')

    @action(detail=True, url_path='report-types')
    def get_report_types(self, request, pk):
        """
        Provides a list of report types associated with this platform
        """
        platform = get_object_or_404(Platform.objects.all(), pk=pk)
        report_types = ReportType.objects.filter(interest_platforms=platform).\
            prefetch_related('reportinterestmetric_set__metric',
                             'reportinterestmetric_set__interest_group')
        # for rt in report_types:
        #     rt.used_metrics = Metric.objects.\
        #         filter(pk__in=AccessLog.objects.filter(report_type=rt, platform=platform).
        #                values('metric').distinct())
        return Response(ReportTypeExtendedSerializer(report_types, many=True).data)


class PlatformViewSet(ReadOnlyModelViewSet):

    serializer_class = PlatformSerializer

    def get_queryset(self):
        """
        Should return only platforms for the requested organization
        """
        org_filter = organization_filter_from_org_id(self.kwargs.get('organization_pk'),
                                                     self.request.user)
        return Platform.objects.filter(**org_filter)

    @action(methods=['GET'], url_path='no-interest-defined', detail=False)
    def without_interest_definition(self, request, organization_pk):
        org_filter = organization_filter_from_org_id(organization_pk, request.user)
        import_batch_query = ImportBatch.objects.filter(platform_id=OuterRef('pk'))
        qs = Platform.objects.\
            filter(**org_filter, interest_reports__isnull=True).\
            annotate(has_data=Exists(import_batch_query))
        return Response(DetailedPlatformSerializer(qs, many=True).data)

    @action(methods=['GET'], url_path='title-count', detail=False)
    def title_count(self, request, organization_pk):
        org_filter = organization_filter_from_org_id(organization_pk, request.user)
        date_filter_params = date_filter_from_params(request.GET)
        qs = PlatformTitle.objects.\
            filter(**org_filter, **date_filter_params).\
            values('platform').\
            annotate(title_count=Count('title', distinct=True))
        return Response(qs)

    @action(methods=['GET'], url_path='title-count', detail=True)
    def title_count_detail(self, request, organization_pk, pk):
        org_filter = organization_filter_from_org_id(organization_pk, request.user)
        date_filter_params = date_filter_from_params(request.GET)
        qs = PlatformTitle.objects.\
            filter(platform_id=pk, **org_filter, **date_filter_params).\
            values('platform').\
            annotate(title_count=Count('title', distinct=True))
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
        org_filter = organization_filter_from_org_id(self.kwargs.get('organization_pk'),
                                                     self.request.user)
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
            result = Platform.objects.filter(**org_filter).filter(**prefilter). \
                annotate(title_count=Count('accesslog__target', distinct=True,
                                           filter=Q(**count_filter)),
                         **interest_annot_params)
            extract_interests_from_objects(interest_rt, result)
        else:
            # we are filtering by ID and thus getting only one object
            # in this case we drop the prefilter so that it is possible to get data
            # for platforms that are not connected to the organization
            result = Platform.objects.filter(**org_filter).\
                annotate(title_count=Count('accesslog__target', distinct=True,
                                           filter=Q(**count_filter)),
                         **interest_annot_params)
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
            interest_type.text:
                Coalesce(
                    Sum('value', filter=Q(dim1=interest_type.pk, report_type=interest_rt)),
                    0)
            for interest_type in interest_type_dim.dimensiontext_set.filter(text__in=ig_names)
        }
        return interest_rt, interest_annot_params

    def get_queryset(self, request, organization_pk):
        org_filter = organization_filter_from_org_id(organization_pk, request.user)
        date_filter_params = date_filter_from_params(request.GET)
        interest_rt, interest_annot_params = self.get_report_type_and_filters()
        result = AccessLog.objects\
            .filter(**org_filter, **date_filter_params, report_type=interest_rt)\
            .values('platform')\
            .annotate(**interest_annot_params)
        return result

    def list(self, request, organization_pk):
        qs = self.get_queryset(request, organization_pk)
        data_format = request.GET.get('format')
        if data_format in ('csv', 'xlsx'):
            # when exporting, we want to rename the columns and rows
            data = DataFrame(qs)
            platform_names = {pl['pk']: pl['short_name']
                              for pl in Platform.objects.all().values('pk', 'short_name')}
            metric_names = {m['short_name']: m['name']
                            for m in InterestGroup.objects.all().values('short_name', 'name')}
            data['platform'] = [platform_names[pk] for pk in data['platform']]
            data.set_index('platform', drop=True, inplace=True)
            data.rename(columns=metric_names, inplace=True)
            return Response(data,
                            headers={
                                'Content-Disposition':
                                    f'attachment; filename="export.{data_format}"'
                            })
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
        result = AccessLog.objects\
            .filter(report_type=interest_rt, **org_filter, platform_id=pk)\
            .values('date__year')\
            .annotate(**interest_annot_params)
        return Response(result)

    @action(detail=False, url_path='by-year')
    def list_by_year(self, request, organization_pk):
        """
        Provides a list of report types associated with this platform
        """
        interest_rt, interest_annot_params = self.get_report_type_and_filters()
        org_filter = organization_filter_from_org_id(organization_pk, request.user)
        result = AccessLog.objects\
            .filter(report_type=interest_rt, **org_filter)\
            .values('platform', 'date__year')\
            .annotate(**interest_annot_params)
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
        self.org_filter = organization_filter_from_org_id(self.kwargs.get('organization_pk'),
                                                          self.request.user)
        self.date_filter = date_filter_from_params(self.request.GET)
        # run stuff before we start creating the queryset
        self._before_queryset()
        # put together filters for title itself
        search_filters = []
        q = self.request.query_params.get('q')
        if q:
            search_filters = [Q(name__ilike=p) | Q(isbn__ilike=p) | Q(issn__ilike=p) |\
                              Q(doi__ilike=p) for p in q.split()]
        pub_type_arg = self.request.query_params.get('pub_type')
        if pub_type_arg:
            search_filters.append(Q(pub_type=pub_type_arg))
        # we evaluate this here as it might be important for the _extra_accesslog_filters method
        extra_filters = self._extra_filters()
        # put together filters for accesslogs
        accesslog_filter = {
            **self._extra_accesslog_filters()
        }
        title_qs = Title.objects.all()
        if accesslog_filter:
            # we have some filters for accesslog - this means we have to add the relevant
            # accesslogs to the queryset
            accesslog_filter.update(**extend_query_filter(self.date_filter, 'accesslog__'))
            title_qs = title_qs.annotate(
                relevant_accesslogs=FilteredRelation('accesslog',
                                                     condition=Q(**accesslog_filter))
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
        ).distinct()
        result = title_qs.filter(pk__in=base_title_query)
        annot = self._annotations()
        if annot:
            result = result.annotate(**annot)
        result = self._postprocess(result)
        return result

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
        self.platform = get_object_or_404(Platform.objects.filter(**self.org_filter),
                                          pk=self.kwargs['platform_pk'])
        # filters['accesslog__platform'] = platform
        filters['platformtitle__platform'] = self.platform
        return filters


class TitleInterestMixin(object):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.interest_rt = None
        self.interest_type_dim = None
        self.interest_groups_names = set()

    def _before_queryset(self):
        self.interest_rt = ReportType.objects.get(short_name='interest', source__isnull=True)
        self.interest_type_dim = self.interest_rt.dimensions_sorted[0]
        self.interest_groups_names = {x['short_name']
                                      for x in InterestGroup.objects.all().values('short_name')}

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
            interest_type.text:
                Coalesce(
                    Sum('relevant_accesslogs__value',
                        filter=Q(relevant_accesslogs__dim1=interest_type.pk)
                        ),
                    0)
            for interest_type in
            self.interest_type_dim.dimensiontext_set.filter(text__in=self.interest_groups_names)
        }
        annotations.update(interest_annot_params)
        return annotations

    def _postprocess_paginated(self, result):
        interest_types = {
            interest_type.text for interest_type in
            self.interest_type_dim.dimensiontext_set.filter(text__in=self.interest_groups_names)
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
        org_filter = organization_filter_from_org_id(self.kwargs.get('organization_pk'),
                                                     self.request.user)
        extra_filters = self._extra_filters(org_filter)
        access_log_filter = Q(**org_filter, **extra_filters)
        distinct_rts = AccessLog.objects.filter(access_log_filter).\
            values('report_type_id').distinct()
        report_types = ReportDataView.objects.filter(base_report_type_id__in=distinct_rts)
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
        platform = get_object_or_404(Platform.objects.filter(**org_filter),
                                     pk=self.kwargs['platform_pk'])
        return {'platform': platform}


class PlatformTitleReportDataViewViewSet(BaseReportDataViewViewSet):
    """
    Provides a list of report types for specific title for specific organization and platform
    """

    def _extra_filters(self, org_filter):
        platform = get_object_or_404(Platform.objects.filter(**org_filter),
                                     pk=self.kwargs['platform_pk'])
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
            **extend_query_filter(org_filter, 'accesslog__')
        ).distinct()
        return Response(PlatformSerializer(platforms, many=True).data)


class TitleInterestViewSet(TitleInterestMixin, BaseTitleViewSet):
    """
    View for all titles for selected organization
    """

    serializer_class = TitleCountSerializer
    pagination_class = SmartResultsSetPagination


class StartERMSSyncPlatformsTask(APIView):

    permission_classes = [SuperuserOrAdminPermission]

    def post(self, request):
        task = erms_sync_platforms_task.delay()
        return Response({
            'id': task.id,
        })
