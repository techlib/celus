from itertools import groupby

from django.db.models import Count, Q
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from core.permissions import SuperuserOrAdminPermission
from organizations.logic.queries import organization_filter_from_org_id
from organizations.tasks import erms_sync_organizations_task
from sushi.models import SushiCredentials
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

    @action(detail=True, url_path='sushi-credentials-versions')
    def sushi_credentials_versions(self, request, pk):
        org_filter = organization_filter_from_org_id(pk, request.user)
        data = SushiCredentials.objects.filter(**org_filter).annotate(count=Count('pk')).\
            values('platform', 'counter_version', 'outside_consortium', 'count').filter(count__gt=0)
        print(data)
        result = {}
        for rec in data:
            if rec['platform'] not in result:
                result[rec['platform']] = []
            result[rec['platform']].append({
                'version': rec['counter_version'],
                 'outside_consortium': rec['outside_consortium']
            })
        for key, value in result.items():
            value.sort(key=lambda x: x['version'])
        return Response(result)



class StartERMSSyncOrganizationsTask(APIView):

    permission_classes = [SuperuserOrAdminPermission]

    def post(self, request):
        task = erms_sync_organizations_task.delay()
        return Response({
            'id': task.id,
        })
