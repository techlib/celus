from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet

from .serializers import OrganizationSerializer


class OrganizationViewSet(ReadOnlyModelViewSet):

    serializer_class = OrganizationSerializer

    def get_queryset(self):
        """
        Should return only organizations associated with the current user
        :return:
        """
        return self.request.user.accessible_organizations().order_by('name')
