from rest_framework.serializers import ModelSerializer

from organizations.serializers import OrganizationSerializer
from publications.serializers import PlatformSerializer
from .models import SushiCredentials, CounterReportType, SushiFetchAttempt


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


class SushiFetchAttemptSerializer(ModelSerializer):

    counter_report = CounterReportTypeSerializer(read_only=True)
    organization = OrganizationSerializer(read_only=True, source='credentials.organization')

    class Meta:
        model = SushiFetchAttempt
        fields = ('timestamp', 'start_date', 'end_date', 'success', 'queued', 'is_processed',
                  'when_processed', 'when_queued', 'counter_report', 'organization', 'log',
                  'import_batch')
