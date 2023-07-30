from rest_framework.serializers import ModelSerializer

from export.models import FlexibleDataExport


class FlexibleDataExportSerializer(ModelSerializer):
    class Meta:
        model = FlexibleDataExport
        fields = (
            'pk',
            'name',
            'created',
            'last_updated',
            'status',
            'output_file',
            'export_params',
            'progress',
            'file_size',
            'file_format',
            'error_info',
        )
