from rest_framework.serializers import ModelSerializer

from organizations.serializers import OrganizationSerializer
from publications.serializers import PlatformSerializer
from .models import SushiCredentials, CounterReportType


class CounterReportTypeSerializer(ModelSerializer):

    class Meta:
        model = CounterReportType
        fields = ('id', 'code', 'name', 'counter_version')


class SushiCredentialsSerializer(ModelSerializer):

    organization = OrganizationSerializer(read_only=True)
    platform = PlatformSerializer(read_only=True)
    active_counter_reports_long = \
        CounterReportTypeSerializer(many=True, source='active_counter_reports', read_only=True)

    class Meta:
        model = SushiCredentials
        fields = ('id', 'organization', 'platform', 'enabled', 'url', 'counter_version',
                  'requestor_id', 'customer_id', 'http_username', 'http_password', 'api_key',
                  'extra_params', 'active_counter_reports', 'active_counter_reports_long')

    def update(self, instance, validated_data):
        active_reports = validated_data.pop('active_counter_reports')
        result = super().update(instance, validated_data)  # type: SushiCredentials
        result.active_counter_reports.set(active_reports)
        return result
