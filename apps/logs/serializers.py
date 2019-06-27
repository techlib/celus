from rest_framework.fields import CharField
from rest_framework.serializers import ModelSerializer

from .models import Metric, Dimension, ReportType


class MetricSerializer(ModelSerializer):

    class Meta:
        model = Metric
        fields = ('pk', 'short_name', 'name')


class DimensionSerializer(ModelSerializer):

    type = CharField(source='get_type_display')

    class Meta:
        model = Dimension
        fields = ('pk', 'short_name', 'name', 'type')


class ReportTypeSerializer(ModelSerializer):

    dimensions_sorted = DimensionSerializer(many=True, read_only=True)

    class Meta:
        model = ReportType
        fields = ('pk', 'short_name', 'name', 'desc', 'dimensions_sorted')

