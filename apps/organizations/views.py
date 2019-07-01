from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Organization
from .serializers import OrganizationSerializer


class OrganizationViewSet(ReadOnlyModelViewSet):

    serializer_class = OrganizationSerializer

    def get_queryset(self):
        """
        Should return only organizations associated with the current user
        :return:
        """
        user = self.request.user
        return user.organizations.all()

