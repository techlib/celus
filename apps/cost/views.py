from django.shortcuts import get_object_or_404
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Payment
from .serializers import PaymentSerializer


class OrganizationPaymentViewSet(ReadOnlyModelViewSet):

    serializer_class = PaymentSerializer
    queryset = Payment.objects.none()

    def get_queryset(self):
        organization = get_object_or_404(self.request.user.accessible_organizations(),
                                         pk=self.kwargs.get('organization_pk'))
        return organization.payment_set.all()

