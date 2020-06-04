from rest_framework.fields import BooleanField
from rest_framework.serializers import ModelSerializer

from .models import ReportDataView, ChartDefinition
from logs.serializers import DimensionSerializer


class ReportDataViewSerializer(ModelSerializer):

    public = BooleanField(default=False)
    primary_dimension = DimensionSerializer(read_only=True)

    class Meta:
        model = ReportDataView
        fields = (
            'pk',
            'short_name',
            'name',
            'name_cs',
            'name_en',
            'desc',
            'public',
            'primary_dimension',
            'is_standard_view',
            'position',
        )


class ChartDefinitionSerializer(ModelSerializer):

    primary_dimension = DimensionSerializer(read_only=True)
    secondary_dimension = DimensionSerializer(read_only=True)

    class Meta:
        model = ChartDefinition
        fields = (
            'pk',
            'name',
            'desc',
            'primary_dimension',
            'primary_implicit_dimension',
            'secondary_dimension',
            'secondary_implicit_dimension',
            'chart_type',
            'ordering',
            'ignore_organization',
            'ignore_platform',
            'scope',
        )
