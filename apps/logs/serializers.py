from rest_framework.serializers import ModelSerializer

from .models import Metric


class MetricSerializer(ModelSerializer):

    class Meta:
        model = Metric
        fields = ('pk', 'short_name', 'name')
