from django.db.models import Count, Sum, Q, F, ExpressionWrapper, FloatField
from django.db.models.functions import Cast
from rest_framework.generics import get_object_or_404
from rest_framework.viewsets import ReadOnlyModelViewSet

from core.logic.dates import date_filter_from_params
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
        sum_filter = {'accesslog__organization': organization}
        date_filter_params = date_filter_from_params(self.request.GET, key_start='accesslog__')
        if date_filter_params:
            sum_filter.update(date_filter_params)
        return organization.platforms.all(). \
            annotate(title_count=Count('accesslog__target', distinct=True),
                     interest=Sum('accesslog__value', filter=Q(**sum_filter)),
                     rel_interest=ExpressionWrapper(
                         (Cast('interest', FloatField()) / F('title_count')),
                         output_field=FloatField()))  # cast to float to prevent integer division


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
            date_filter = Q(**date_filter_params)
        else:
            date_filter = None
        return Title.objects.filter(accesslog__platform=platform,
                                    accesslog__organization=organization).\
            distinct().annotate(count=Sum('accesslog__value', filter=date_filter))
