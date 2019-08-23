from django.db.models import Count, Q
from rest_framework.viewsets import ReadOnlyModelViewSet

from .serializers import OrganizationSerializer


class OrganizationViewSet(ReadOnlyModelViewSet):

    serializer_class = OrganizationSerializer

    def get_queryset(self):
        """
        Should return only organizations associated with the current user
        :return:
        """
        return self.request.user.accessible_organizations().annotate(
            is_admin=Count('userorganization',
                           filter=Q(userorganization__is_admin=True,
                                    userorganization__user=self.request.user))
            ).order_by('name')
