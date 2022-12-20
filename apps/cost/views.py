from core.permissions import (
    CanAccessOrganizationRelatedObjectPermission,
    CanPostOrganizationDataPermission,
    OrganizationRequiredInDataForNonSuperusers,
    SuperuserOrAdminPermission,
)
from django.db.models import Sum
from organizations.logic.queries import organization_filter_from_org_id
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import Payment
from .serializers import PaymentSerializer


class OrganizationPaymentViewSet(ModelViewSet):

    serializer_class = PaymentSerializer
    queryset = Payment.objects.none()
    permission_classes = [
        IsAuthenticated
        & (
            SuperuserOrAdminPermission
            | (CanPostOrganizationDataPermission & CanAccessOrganizationRelatedObjectPermission)
        )
    ]

    def get_queryset(self):
        org_filter = organization_filter_from_org_id(
            self.kwargs.get('organization_pk'), self.request.user
        )
        return Payment.objects.filter(**org_filter)

    @action(detail=False, url_path='by-year')
    def list_by_year(self, request, organization_pk):
        org_filter = organization_filter_from_org_id(organization_pk, request.user)
        qs = (
            Payment.objects.filter(**org_filter)
            .values('platform', 'year')
            .annotate(price=Sum('price'))
        )
        return Response(qs)
