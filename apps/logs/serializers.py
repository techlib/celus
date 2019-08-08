from rest_framework.fields import CharField, IntegerField, DateField
from rest_framework.relations import StringRelatedField
from rest_framework.serializers import ModelSerializer, BaseSerializer

from logs.models import AccessLog
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
    log_count = IntegerField(read_only=True)
    newest_log = DateField(read_only=True)
    oldest_log = DateField(read_only=True)

    class Meta:
        model = ReportType
        fields = ('pk', 'short_name', 'name', 'desc', 'dimensions_sorted', 'log_count',
                  'newest_log', 'oldest_log')


class AccessLogSerializer(BaseSerializer):

    report_type = StringRelatedField()
    organization = StringRelatedField()
    platform = StringRelatedField()
    metric = StringRelatedField()
    target = StringRelatedField()

    class Meta:
        model = AccessLog
        # fields = ('date', 'report_type', 'organization', 'platform', 'target', 'value')

    def to_representation(self, obj: AccessLog):
        data = {
            'date': obj.date.isoformat(),
            'report_type': str(obj.report_type),
            'platform': str(obj.platform),
            'organization': str(obj.organization),
            'target': str(obj.target),
            'value': obj.value
        }
        data.update(getattr(obj, 'mapped_dim_values_', {}))
        return data

    def get_fields(self):
        return []
