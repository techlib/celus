from organizations.logic.queries import organization_filter_from_org_id
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import AccessLogExport, AccessLogExportBatch
from .serializers import AccessLogExportBatchProgressSerializer, AccessLogExportSerializer


class AccessLogExportViewSet(ReadOnlyModelViewSet):
    serializer_class = AccessLogExportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        all_exports = AccessLogExport.objects.all()
        org_filter = {}
        if org_id := self.request.query_params.get("organization"):
            # this already checks if the user has access to the organization
            org_filter = organization_filter_from_org_id(org_id, user, admin_required=True)
        elif not user.is_admin_of_master_organization and not user.is_superuser:
            # this is a fallback for non-admin users who access the API without organization filter
            org_filter = {"organization__in": user.admin_organizations()}
        return all_exports.filter(**org_filter)

    @action(detail=True, methods=["post"])
    def start_export(self, request, pk):
        """
        Start export for a specific export by creating a new batch and starting the tasks.
        It returns the progress information for the new batch.
        """
        export = self.get_object()
        user = request.user

        # Check if superuser and task is running
        if user.is_superuser and export.has_running_tasks:
            return Response(
                {
                    "detail": "Export cannot be started because a task is already running.",
                    "next_export_available_at": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if normal admin can start export
        if not user.is_superuser and not export.can_start_export(user):
            next_available = export.get_next_export_available_at(user)
            response_data = {
                "detail": (
                    "Export cannot be started yet. Please wait for the cooldown period to expire."
                ),
                "next_export_available_at": next_available and next_available.isoformat(),
            }
            return Response(response_data, status=status.HTTP_403_FORBIDDEN)

        batch = export.create_batch(start_tasks=True)
        return Response(
            AccessLogExportBatchProgressSerializer(batch).data, status=status.HTTP_201_CREATED
        )


class AccessLogExportBatchProgressView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        """
        Get progress information for a specific export batch.
        """
        # Prefetch tasks with report types for better performance
        try:
            batch = (
                AccessLogExportBatch.objects.select_related("export")
                .prefetch_related("tasks__report_type")
                .get(pk=pk)
            )
        except AccessLogExportBatch.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        # Check permissions - user must have access to the export
        user = request.user
        export = batch.export
        all_exports = AccessLogExport.objects.all()
        if user.is_admin_of_master_organization or user.is_superuser:
            accessible_exports = all_exports  # including consortial (full) export
        else:
            accessible_exports = all_exports.filter(organization__in=user.admin_organizations())

        if export not in accessible_exports:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AccessLogExportBatchProgressSerializer(batch)
        return Response(serializer.data)
