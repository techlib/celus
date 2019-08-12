from django.db.models import Count, Sum, Q, F, ExpressionWrapper, FloatField, Max, Min
from django.db.models.functions import Cast
from django.http import Http404
from rest_framework.generics import get_object_or_404
from rest_framework.viewsets import ReadOnlyModelViewSet

from core.logic.dates import date_filter_from_params
from logs.logic.queries import interest_group_annotation_params, extract_interests_from_objects
from logs.models import ReportType, InterestGroup
from logs.serializers import ReportTypeSerializer
from organizations.logic.queries import organization_filter_from_org_id, extend_query_filter
from publications.models import Platform, Title
from publications.serializers import TitleCountSerializer
from .serializers import PlatformSerializer, DetailedPlatformSerializer, TitleSerializer


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
        count_filter['accesslog__metric__interest_group__isnull'] = False   # for counting titles
        # parameters for annotation defining an annotation for each of the interest groups
        interests = InterestGroup.objects.all()
        interest_annot_params = interest_group_annotation_params(interests, count_filter)
        # add more filters for dates
        date_filter_params = date_filter_from_params(self.request.GET, key_start='accesslog__')
        if date_filter_params:
            count_filter.update(date_filter_params)
        result = Platform.objects.filter(**org_filter).filter(**count_filter).\
            annotate(title_count=Count('accesslog__target', distinct=True,
                                       filter=Q(**count_filter)),
                     **interest_annot_params).\
            filter(title_count__gt=0)
        # the following creates the interest dict attr from the interest annotations
        extract_interests_from_objects(interests, result)
        return result


class PlatformTitleViewSet(ReadOnlyModelViewSet):

    serializer_class = TitleSerializer

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

    def _extra_filters(self):
        return {}

    def get_queryset(self):
        org_filter = organization_filter_from_org_id(self.kwargs.get('organization_pk'),
                                                     self.request.user)
        platform = get_object_or_404(Platform.objects.filter(**org_filter),
                                     pk=self.kwargs['platform_pk'])
        access_log_filter = Q(accesslog__platform=platform,
                              **extend_query_filter(org_filter, 'accesslog__'),
                              **self._extra_filters())
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

    pass


class PlatformTitleReportTypeViewSet(BaseReportTypeViewSet):
    """
    Provides a list of report types for specific title for specific organization and platform
    """

    serializer_class = ReportTypeSerializer

    def _extra_filters(self):
        title = get_object_or_404(Title.objects.all(), pk=self.kwargs['title_pk'])
        return {'accesslog__target': title}


class TitleReportTypeViewSet(ReadOnlyModelViewSet):
    """
    Provides a list of report types for specific title for specific organization
    """

    serializer_class = ReportTypeSerializer

    def get_queryset(self):
        organization = get_object_or_404(self.request.user.organizations.all(),
                                         pk=self.kwargs['organization_pk'])
        title = get_object_or_404(Title.objects.all(), pk=self.kwargs['title_pk'])
        access_log_filter = Q(accesslog__organization=organization,
                              accesslog__metric__active=True)    # TODO: x
        report_types = ReportType.objects.filter(accesslog__target=title).\
            annotate(log_count=Count('accesslog__value', filter=access_log_filter),
                     newest_log=Max('accesslog__date', filter=access_log_filter),
                     oldest_log=Min('accesslog__date', filter=access_log_filter),
                     ).\
            filter(log_count__gt=0).order_by('-newest_log')
        return report_types


class TitleViewSet(ReadOnlyModelViewSet):

    serializer_class = TitleSerializer

    def get_queryset(self):
        """
        Should return only titles for specific organization but all platforms
        """
        organization = get_object_or_404(self.request.user.organizations.all(),
                                         pk=self.kwargs['organization_pk'])
        return Title.objects.filter(accesslog__organization=organization).distinct()


class TitleCountsViewSet(ReadOnlyModelViewSet):
    """
    View for all titles for selected organization
    """

    serializer_class = TitleCountSerializer

    def get_queryset(self):
        """
        Should return only titles for specific organization but all platforms
        """
        organization = get_object_or_404(self.request.user.organizations.all(),
                                         pk=self.kwargs['organization_pk'])
        date_filter_params = date_filter_from_params(self.request.GET, key_start='accesslog__')
        return Title.objects.filter(accesslog__organization=organization,
                                    accesslog__metric__interest_group__isnull=False,
                                    **date_filter_params).\
            distinct().annotate(interest=Sum('accesslog__value'))

