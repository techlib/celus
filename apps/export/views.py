from pprint import pprint

from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_201_CREATED
from rest_framework.viewsets import ModelViewSet

from logs.logic.queries import FlexibleDataSlicer, SlicerConfigError
from .models import FlexibleDataExport
from .serializers import FlexibleDataExportSerializer
from .tasks import process_flexible_export_task


class FlexibleDataExportViewSet(ModelViewSet):

    queryset = FlexibleDataExport.objects.none()
    serializer_class = FlexibleDataExportSerializer

    def get_queryset(self):
        return FlexibleDataExport.objects.filter(owner=self.request.user).order_by('-created')

    def create(self, request, *args, **kwargs):
        try:
            slicer = FlexibleDataSlicer.create_from_params(request.data)
        except SlicerConfigError as e:
            return Response({'error': str(e)}, status=HTTP_400_BAD_REQUEST)
        export = FlexibleDataExport.create_from_slicer(slicer, request.user)
        process_flexible_export_task.apply_async(args=(export.pk,), countdown=2)
        serializer = self.get_serializer(export)
        return Response(serializer.data, status=HTTP_201_CREATED)
