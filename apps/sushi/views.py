from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from organizations.logic.queries import organization_filter_from_org_id
from sushi.models import CounterReportType
from sushi.serializers import CounterReportTypeSerializer
from .models import SushiCredentials
from .serializers import SushiCredentialsSerializer


class SushiCredentialsViewSet(ModelViewSet):

    serializer_class = SushiCredentialsSerializer
    queryset = SushiCredentials.objects.none()

    def get_queryset(self):
        user_organizations = self.request.user.accessible_organizations()
        qs = SushiCredentials.objects.filter(organization__in=user_organizations).\
            select_related('organization', 'platform').prefetch_related('active_counter_reports')
        organization_id = self.request.query_params.get('organization')
        if organization_id:
            qs = qs.filter(**organization_filter_from_org_id(organization_id, self.request.user))
        return qs


class CounterReportTypeViewSet(ReadOnlyModelViewSet):

    serializer_class = CounterReportTypeSerializer
    queryset = CounterReportType.objects.all()
