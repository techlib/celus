from rest_framework.exceptions import PermissionDenied
from rest_framework.fields import (
    HiddenField,
    CurrentUserDefault,
    BooleanField,
    SerializerMethodField,
)
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.serializers import ModelSerializer

from core.models import UL_CONS_STAFF
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
    active_counter_reports_long = CounterReportTypeSerializer(
        many=True, source='active_counter_reports', read_only=True
    )
    organization_id = PrimaryKeyRelatedField(
        source='organization', write_only=True, queryset=Organization.objects.all()
    )
    platform_id = PrimaryKeyRelatedField(
        source='platform', write_only=True, queryset=Platform.objects.all()
    )
    locked_for_me = BooleanField(read_only=True)
    can_lock = BooleanField(read_only=True)
    submitter = HiddenField(default=CurrentUserDefault())
    locked = SerializerMethodField()

    class Meta:
        model = SushiCredentials
        fields = (
            'pk',
            'organization',
            'platform',
            'enabled',
            'url',
            'counter_version',
            'requestor_id',
            'customer_id',
            'http_username',
            'http_password',
            'api_key',
            'extra_params',
            'active_counter_reports',
            'active_counter_reports_long',
            'organization_id',
            'platform_id',
            'submitter',
            'locked_for_me',
            'lock_level',
            'can_lock',
            'locked',
            'outside_consortium',
        )

    def get_locked(self, obj: SushiCredentials):
        return obj.lock_level >= UL_CONS_STAFF

    def update(self, instance: SushiCredentials, validated_data):
        submitter = validated_data.pop('submitter', None) or self.context['request'].user
        if not instance.can_edit(submitter):
            raise PermissionDenied('User is not allowed to edit this object - it is locked.')
        result = super().update(instance, validated_data)  # type: SushiCredentials
        result.last_updated_by = submitter
        result.save()
        submitter_level = submitter.organization_relationship(result.organization_id)
        result.can_lock = submitter_level >= UL_CONS_STAFF
        result.locked_for_me = submitter_level < result.lock_level
        return result

    def create(self, validated_data):
        submitter = validated_data.pop('submitter')
        result = super().create(validated_data)
        result.last_updated_by = submitter
        result.save()
        submitter_level = submitter.organization_relationship(result.organization_id)
        result.can_lock = submitter_level >= UL_CONS_STAFF
        result.locked_for_me = submitter_level < result.lock_level
        return result


class SushiFetchAttemptSerializer(ModelSerializer):

    counter_report_verbose = CounterReportTypeSerializer(read_only=True, source='counter_report')
    organization = OrganizationSerializer(read_only=True, source='credentials.organization')

    class Meta:
        model = SushiFetchAttempt
        fields = (
            'pk',
            'timestamp',
            'start_date',
            'end_date',
            'download_success',
            'error_code',
            'contains_data',
            'queued',
            'is_processed',
            'when_processed',
            'when_queued',
            'counter_report',
            'organization',
            'log',
            'import_batch',
            'data_file',
            'processing_success',
            'in_progress',
            'counter_report_verbose',
            'credentials',
        )
