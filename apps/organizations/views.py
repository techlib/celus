from django.db.models import Count, Q
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from core.permissions import SuperuserOrAdminPermission
from organizations.tasks import erms_sync_organizations_task
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
                                    userorganization__user=self.request.user)),
            is_member=Count('userorganization',
                            filter=Q(userorganization__user=self.request.user))
            ).order_by('name')


class StartERMSSyncOrganizationsTask(APIView):

    permission_classes = [SuperuserOrAdminPermission]

    def post(self, request):
        task = erms_sync_organizations_task.delay()
        return Response({
            'id': task.id,
        })
