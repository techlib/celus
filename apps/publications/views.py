from django.db.models import Count, Sum, Q, F, ExpressionWrapper, FloatField, Max, Min
from django.db.models.functions import Cast
from rest_framework.generics import get_object_or_404
from rest_framework.viewsets import ReadOnlyModelViewSet

from core.logic.dates import date_filter_from_params
from logs.logic.queries import interest_group_annotation_params, extract_interests_from_objects
from logs.models import ReportType, InterestGroup
from logs.serializers import ReportTypeSerializer
from publications.models import Platform, Title
from publications.serializers import TitleCountSerializer
from .serializers import PlatformSerializer, DetailedPlatformSerializer, TitleSerializer


class PlatformViewSet(ReadOnlyModelViewSet):

    serializer_class = PlatformSerializer

    def get_queryset(self):
        """
        Should return only platforms for the requested organization
        """
        organization = get_object_or_404(self.request.user.organizations.all(),
                                         pk=self.kwargs['organization_pk'])
        return organization.platforms.all()


class DetailedPlatformViewSet(ReadOnlyModelViewSet):

    serializer_class = DetailedPlatformSerializer

    def get_queryset(self):
        """
        Should return only platforms for the requested organization.
        Should include title_count which counts titles on the platform
        """
        organization = get_object_or_404(self.request.user.organizations.all(),
                                         pk=self.kwargs['organization_pk'])
        # filters for the suitable access logs
        count_filter = {'accesslog__organization': organization,
                        'accesslog__metric__interest_group__isnull': False}   # for counting titles
        # parameters for annotation defining an annotation for each of the interest groups
        interests = InterestGroup.objects.all()
        interest_annot_params = interest_group_annotation_params(interests, count_filter)
        # add more filters for dates
        date_filter_params = date_filter_from_params(self.request.GET, key_start='accesslog__')
        if date_filter_params:
            count_filter.update(date_filter_params)
        result = organization.platforms.all().filter(**count_filter).\
            annotate(title_count=Count('accesslog__target', distinct=True,
                                       filter=Q(**count_filter)),
                     **interest_annot_params).\
            filter(title_count__gt=0)
        # the following creates the interest dict attr from the interest annotations
        extract_interests_from_objects(interests, result)
        return result


class PlatformTitleViewSet(ReadOnlyModelViewSet):

    serializer_class = TitleSerializer

    def get_queryset(self):
        """
        Should return only titles for specific organization and platform
        """
        organization = get_object_or_404(self.request.user.organizations.all(),
                                         pk=self.kwargs['organization_pk'])
        platform = get_object_or_404(organization.platforms.all(),
                                     pk=self.kwargs['platform_pk'])
        return Title.objects.filter(accesslog__platform=platform,
                                    accesslog__organization=organization).distinct()


class PlatformTitleCountsViewSet(ReadOnlyModelViewSet):

    serializer_class = TitleCountSerializer

    def get_queryset(self):
        """
        Should return only titles for specific organization and platform
        """
        organization = get_object_or_404(self.request.user.organizations.all(),
                                         pk=self.kwargs['organization_pk'])
        platform = get_object_or_404(organization.platforms.all(),
                                     pk=self.kwargs['platform_pk'])
        date_filter_params = date_filter_from_params(self.request.GET, key_start='accesslog__')
        if date_filter_params:
            sum_filter = date_filter_params
        else:
            sum_filter = {}
        # when calculating interest in Titles, we do not distinguish between different types
        # of interest, because one title should have only one valid interest group
        result = Title.objects.filter(accesslog__platform=platform,
                                      accesslog__organization=organization,
                                      accesslog__metric__interest_group__isnull=False).\
            distinct().annotate(interest=Sum('accesslog__value'))
        return result


class PlatformReportTypeViewSet(ReadOnlyModelViewSet):
    """
    Provides a list of report types for specific title for specific organization and platform
    """

    serializer_class = ReportTypeSerializer

    def get_queryset(self):
        organization = get_object_or_404(self.request.user.organizations.all(),
                                         pk=self.kwargs['organization_pk'])
        platform = get_object_or_404(organization.platforms.all(),
                                     pk=self.kwargs['platform_pk'])
        access_log_filter = Q(accesslog__platform=platform, accesslog__organization=organization)
        report_types = ReportType.objects.filter(access_log_filter).\
            annotate(log_count=Count('accesslog__value', filter=access_log_filter),
                     newest_log=Max('accesslog__date', filter=access_log_filter),
                     oldest_log=Min('accesslog__date', filter=access_log_filter),
                     ).\
            filter(log_count__gt=0).order_by('-newest_log')
        return report_types


class PlatformTitleReportTypeViewSet(ReadOnlyModelViewSet):
    """
    Provides a list of report types for specific title for specific organization and platform
    """

    serializer_class = ReportTypeSerializer

    def get_queryset(self):
        organization = get_object_or_404(self.request.user.organizations.all(),
                                         pk=self.kwargs['organization_pk'])
        platform = get_object_or_404(organization.platforms.all(),
                                     pk=self.kwargs['platform_pk'])
        title = get_object_or_404(Title.objects.all(), pk=self.kwargs['title_pk'])
        access_log_filter = Q(accesslog__platform=platform, accesslog__organization=organization)
        report_types = ReportType.objects.filter(accesslog__target=title).\
            annotate(log_count=Count('accesslog__value', filter=access_log_filter),
                     newest_log=Max('accesslog__date', filter=access_log_filter),
                     oldest_log=Min('accesslog__date', filter=access_log_filter),
                     ).\
            filter(log_count__gt=0).order_by('-newest_log')
        return report_types


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
        if date_filter_params:
            sum_filter = Q(accesslog__metric__active=True, **date_filter_params)   # TODO: x
        else:
            sum_filter = Q(accesslog__metric__active=True)
        return Title.objects.filter(accesslog__organization=organization).\
            distinct().annotate(count=Sum('accesslog__value', filter=sum_filter))

