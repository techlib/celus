from rest_framework import permissions
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import AccessLogExport
from .serializers import AccessLogExportSerializer


class AccessLogExportViewSet(ReadOnlyModelViewSet):
    serializer_class = AccessLogExportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        all_exports = AccessLogExport.objects.all()
        if user.is_admin_of_master_organization or user.is_superuser:
            return all_exports  # including consortial (full) export
        return all_exports.filter(organization__in=user.admin_organizations())
