from rest_framework import generics, permissions

from .models import AccessLogExport
from .serializers import AccessLogExportSerializer


class AccessLogExportList(generics.ListAPIView):
    serializer_class = AccessLogExportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin_of_master_organization or user.is_superuser:
            return AccessLogExport.objects.all()  # including consortial (full) export
        return AccessLogExport.objects.filter(organization__in=user.admin_organizations())
