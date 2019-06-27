from rest_framework.serializers import ModelSerializer

from .models import Metric, Dimension


class MetricSerializer(ModelSerializer):

    class Meta:
        model = Metric
        fields = ('pk', 'short_name', 'name')


class DimensionSerializer(ModelSerializer):

    class Meta:
        model = Dimension
        fields = ('pk', 'short_name', 'name', 'type')
