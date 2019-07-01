from rest_framework.generics import get_object_or_404
from rest_framework.viewsets import ReadOnlyModelViewSet

from .serializers import PlatformSerializer


class PlatformViewSet(ReadOnlyModelViewSet):

    serializer_class = PlatformSerializer

    def get_queryset(self):
        """
        Should return only platforms for the requested organization
        """
        organization = get_object_or_404(self.request.user.organizations.all(),
                                         pk=self.kwargs['organization_pk'])
        return organization.platforms.all()
