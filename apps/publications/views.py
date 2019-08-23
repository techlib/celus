from django.db.models import Count, Sum, Q, Max, Min
from rest_framework.generics import get_object_or_404
from rest_framework.viewsets import ReadOnlyModelViewSet

from core.logic.dates import date_filter_from_params
from logs.logic.queries import interest_group_annotation_params, extract_interests_from_objects
from logs.models import ReportType, InterestGroup
from logs.serializers import ReportTypeSerializer
from logs.views import StandardResultsSetPagination
from organizations.logic.queries import organization_filter_from_org_id, extend_query_filter
from publications.models import Platform, Title
from publications.serializers import TitleCountSerializer
from .serializers import PlatformSerializer, DetailedPlatformSerializer, TitleSerializer


class AllPlatformsViewSet(ReadOnlyModelViewSet):

    serializer_class = PlatformSerializer
    queryset = Platform.objects.all().order_by('name')


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
        org_filter = organization_filter_from_org_id(self.kwargs.get('organization_pk'),
                                                     self.request.user)
        # filters for the suitable access logs
        count_filter = extend_query_filter(org_filter, 'accesslog__')
        # we prefilter using the same filter as for count annotation
        # but without the interest_group filter
        prefilter = dict(count_filter)
        count_filter['accesslog__metric__interest_group__isnull'] = False   # for counting titles
        # parameters for annotation defining an annotation for each of the interest groups
        interests = InterestGroup.objects.all()
        interest_annot_params = interest_group_annotation_params(interests, count_filter)
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
            extract_interests_from_objects(interests, result)
        else:
            # we are filtering by ID and thus getting only one object
            # in this case we drop the count_filter so that it is possible to get data
            # for platforms that are not connected to the organization
            result = Platform.objects.all().\
                annotate(title_count=Count('accesslog__target', distinct=True,
                                           filter=Q(**count_filter)),
                         **interest_annot_params)
        return result

    def get_object(self):
        # we need to enrich the result here as the interests added in get_queryset would not
        # survive the filtering done super().get_object()
        obj = super().get_object()
        interests = InterestGroup.objects.all()
        extract_interests_from_objects(interests, [obj])
        return obj


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


class PlatformTitleCountsViewSet(PlatformTitleViewSet):

    serializer_class = TitleCountSerializer

    def _extra_filters(self):
        return {'accesslog__metric__interest_group__isnull': False}

    def _annotations(self):
        return {'interest': Sum('accesslog__value')}


class BaseReportTypeViewSet(ReadOnlyModelViewSet):
    """
    Provides a list of report types
    """

    serializer_class = ReportTypeSerializer

    def _extra_filters(self, org_filter):
        return {}

    def get_queryset(self):
        org_filter = organization_filter_from_org_id(self.kwargs.get('organization_pk'),
                                                     self.request.user)
        access_log_filter = Q(**extend_query_filter(org_filter, 'accesslog__'),
                              **self._extra_filters(org_filter))
        report_types = ReportType.objects.filter(access_log_filter).\
            annotate(log_count=Count('accesslog__value', filter=access_log_filter),
                     newest_log=Max('accesslog__date', filter=access_log_filter),
                     oldest_log=Min('accesslog__date', filter=access_log_filter),
                     ).\
            filter(log_count__gt=0).order_by('-newest_log')
        return report_types


class PlatformReportTypeViewSet(BaseReportTypeViewSet):
    """
    Provides a list of report types for specific organization and platform
    """

    def _extra_filters(self, org_filter):
        platform = get_object_or_404(Platform.objects.filter(**org_filter),
                                     pk=self.kwargs['platform_pk'])
        return {'accesslog__platform': platform}


class PlatformTitleReportTypeViewSet(BaseReportTypeViewSet):
    """
    Provides a list of report types for specific title for specific organization and platform
    """

    serializer_class = ReportTypeSerializer

    def _extra_filters(self, org_filter):
        platform = get_object_or_404(Platform.objects.filter(**org_filter),
                                     pk=self.kwargs['platform_pk'])
        title = get_object_or_404(Title.objects.all(), pk=self.kwargs['title_pk'])
        return {'accesslog__target': title, 'accesslog__platform': platform}


class TitleReportTypeViewSet(BaseReportTypeViewSet):
    """
    Provides a list of report types for specific title for specific organization
    """

    serializer_class = ReportTypeSerializer

    def _extra_filters(self, org_filter):
        title = get_object_or_404(Title.objects.all(), pk=self.kwargs['title_pk'])
        return {'accesslog__target': title}


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


class TitleCountsViewSet(ReadOnlyModelViewSet):
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
        return Title.objects.filter(accesslog__metric__interest_group__isnull=False,
                                    **extend_query_filter(org_filter, 'accesslog__'),
                                    **date_filter_params).\
            distinct().annotate(interest=Sum('accesslog__value'))

