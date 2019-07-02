from django.db.models import Count
from rest_framework.generics import get_object_or_404
from rest_framework.viewsets import ReadOnlyModelViewSet

from publications.models import Platform, Title
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
        return organization.platforms.all().\
            annotate(title_count=Count('accesslog__target', distinct=True))


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
        return Title.objects.filter(accesslog__platform=platform).distinct()
