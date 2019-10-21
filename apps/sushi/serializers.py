from rest_framework.exceptions import PermissionDenied
from rest_framework.fields import HiddenField, CurrentUserDefault
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.serializers import ModelSerializer

from organizations.models import Organization
from organizations.serializers import OrganizationSerializer
from publications.models import Platform
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
    organization_id = PrimaryKeyRelatedField(source='organization', write_only=True,
                                             queryset=Organization.objects.all())
    platform_id = PrimaryKeyRelatedField(source='platform', write_only=True,
                                         queryset=Platform.objects.all())
    submitter = HiddenField(default=CurrentUserDefault())

    class Meta:
        model = SushiCredentials
        fields = ('id', 'organization', 'platform', 'enabled', 'url', 'counter_version',
                  'requestor_id', 'customer_id', 'http_username', 'http_password', 'api_key',
                  'extra_params', 'active_counter_reports', 'active_counter_reports_long',
                  'organization_id', 'platform_id', 'submitter')

    def update(self, instance: SushiCredentials, validated_data):
        submitter = validated_data.pop('submitter', None) or self.context['request'].user
        if not instance.can_edit(submitter):
            raise PermissionDenied('User is not allowed to edit this object')
        result = super().update(instance, validated_data)  # type: SushiCredentials
        result.last_updated_by = submitter
        result.save()
        return result

    def create(self, validated_data):
        submitter = validated_data.pop('submitter')
        result = super().create(validated_data)
        result.last_updated_by = submitter
        result.save()
        return result



class SushiFetchAttemptSerializer(ModelSerializer):

    counter_report_verbose = CounterReportTypeSerializer(read_only=True, source='counter_report')
    organization = OrganizationSerializer(read_only=True, source='credentials.organization')

    class Meta:
        model = SushiFetchAttempt
        fields = ('pk', 'timestamp', 'start_date', 'end_date', 'download_success', 'error_code',
                  'contains_data', 'queued', 'is_processed', 'when_processed', 'when_queued',
                  'counter_report', 'organization', 'log', 'import_batch', 'data_file',
                  'processing_success', 'in_progress', 'counter_report_verbose', 'credentials')

