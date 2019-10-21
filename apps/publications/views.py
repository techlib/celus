from django.db.models import Count, Sum, Q
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet, ViewSet

from charts.models import ReportDataView
from charts.serializers import ReportDataViewSerializer
from core.logic.dates import date_filter_from_params
from core.permissions import SuperuserOrAdminPermission
from logs.logic.queries import extract_interests_from_objects, interest_annotation_params
from logs.models import ReportType, AccessLog
from logs.serializers import ReportTypeSerializer
from organizations.logic.queries import organization_filter_from_org_id, extend_query_filter
from publications.models import Platform, Title
from publications.serializers import TitleCountSerializer, PlatformSushiCredentialsSerializer
from sushi.models import SushiCredentials
from .serializers import PlatformSerializer, DetailedPlatformSerializer, TitleSerializer
from .tasks import erms_sync_platforms_task


class AllPlatformsViewSet(ReadOnlyModelViewSet):

    serializer_class = PlatformSerializer
    queryset = Platform.objects.all().order_by('name')

    @action(detail=True, url_path='report-types')
    def get_report_types(self, request, pk):
        """
        Provides a list of report types associated with this platform
        """
        platform = get_object_or_404(Platform.objects.all(), pk=pk)
        report_types = ReportType.objects.filter(platform=platform)
        return Response(ReportTypeSerializer(report_types, many=True).data)


class PlatformViewSet(ReadOnlyModelViewSet):

    serializer_class = PlatformSerializer

    def get_queryset(self):
        """
        Should return only platforms for the requested organization
        """
        org_filter = organization_filter_from_org_id(self.kwargs.get('organization_pk'),
                                                     self.request.user)
        return Platform.objects.filter(**org_filter)


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
        count_filter['accesslog__report_type_id'] = interest_rt.pk   # for counting titles
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
            # in this case we drop the count_filter so that it is possible to get data
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

    def get_queryset(self, request, organization_pk):
        interest_rt = ReportType.objects.get(short_name='interest', source__isnull=True)

        org_filter = organization_filter_from_org_id(organization_pk, request.user)
        date_filter_params = date_filter_from_params(request.GET)
        # parameters for annotation defining an annotation for each of the interest groups
        interest_type_dim = interest_rt.dimensions_sorted[0]
        interest_annot_params = {interest_type.text: Sum('value', filter=Q(dim1=interest_type.pk))
                                 for interest_type in interest_type_dim.dimensiontext_set.all()}
        result = AccessLog.objects\
            .filter(report_type=interest_rt, **org_filter, **date_filter_params)\
            .values('platform')\
            .annotate(**interest_annot_params, title_count=Count('target_id', distinct=True))
        return result

    def list(self, request, organization_pk):
        qs = self.get_queryset(request, organization_pk)
        return Response(qs)

    def retrieve(self, request, organization_pk, pk):
        qs = self.get_queryset(request, organization_pk)
        data = qs.filter(platform_id=pk)
        if data:
            return Response(data[0])
        return Response({})


class PlatformTitleViewSet(ReadOnlyModelViewSet):

    serializer_class = TitleSerializer
    # pagination_class = StandardResultsSetPagination

    def _extra_filters(self):
        return {}

    def _annotations(self):
        return {}

    def get_queryset(self):
        """
        Should return only titles for specific organization and platform
        """
        org_filter = organization_filter_from_org_id(self.kwargs.get('organization_pk'),
                                                     self.request.user)
        platform = get_object_or_404(Platform.objects.filter(**org_filter),
                                     pk=self.kwargs['platform_pk'])
        date_filter_params = date_filter_from_params(self.request.GET, key_start='accesslog__')

        result = Title.objects.filter(accesslog__platform=platform,
                                      **date_filter_params,
                                      **extend_query_filter(org_filter, 'accesslog__'),
                                      **self._extra_filters(),
                                      ).distinct()
        annot = self._annotations()
        if annot:
            result = result.annotate(**annot)
        return result


class PlatformTitleInterestViewSet(PlatformTitleViewSet):

    serializer_class = TitleCountSerializer

    def _extra_filters(self):
        return {'accesslog__report_type__short_name': 'interest'}

    def _annotations(self):
        return {'interest': Sum('accesslog__value')}


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
        access_log_filter = Q(**extend_query_filter(org_filter, 'base_report_type__accesslog__'),
                              **extend_query_filter(extra_filters, 'base_report_type__accesslog__')
                              )
        report_types = ReportDataView.objects.filter(access_log_filter).\
            annotate(log_count=Count('base_report_type__accesslog__value',
                                     filter=access_log_filter)
                     ).filter(log_count__gt=0)
        if self.more_precise_results:
            report_types_clean = []
            for rt in report_types:
                if rt.logdata_qs().filter(**org_filter, **extra_filters).exists():
                    report_types_clean.append(rt)
            return report_types_clean
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


class TitleViewSet(ReadOnlyModelViewSet):

    serializer_class = TitleSerializer
    # pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """
        Should return only titles for specific organization but all platforms
        """
        org_filter = organization_filter_from_org_id(self.kwargs.get('organization_pk'),
                                                     self.request.user,
                                                     prefix='accesslog__')
        return Title.objects.filter(**org_filter).distinct()


class TitleInterestViewSet(ReadOnlyModelViewSet):
    """
    View for all titles for selected organization
    """

    serializer_class = TitleCountSerializer
    # pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """
        Should return only titles for specific organization but all platforms
        """
        org_filter = organization_filter_from_org_id(self.kwargs.get('organization_pk'),
                                                     self.request.user)
        date_filter_params = date_filter_from_params(self.request.GET, key_start='accesslog__')
        return Title.objects.filter(accesslog__report_type__short_name='interest',
                                    **extend_query_filter(org_filter, 'accesslog__'),
                                    **date_filter_params).\
            distinct().annotate(interest=Sum('accesslog__value'))


class StartERMSSyncPlatformsTask(APIView):

    permission_classes = [SuperuserOrAdminPermission]

    def post(self, request):
        task = erms_sync_platforms_task.delay()
        return Response({
            'id': task.id,
        })
