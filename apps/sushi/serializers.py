from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.fields import (
    BooleanField,
    CurrentUserDefault,
    DateTimeField,
    HiddenField,
    IntegerField,
    SerializerMethodField,
    IntegerField,
)
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.serializers import ModelSerializer, Serializer


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
            'title',
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
    platform = PlatformSerializer(read_only=True, source='credentials.platform')

    class Meta:
        model = SushiFetchAttempt
        fields = (
            'contains_data',
            'counter_report',
            'counter_report_verbose',
            'credentials',
            'data_file',
            'download_success',
            'end_date',
            'error_code',
            'import_batch',
            'import_crashed',
            'in_progress',
            'is_processed',
            'log',
            'organization',
            'pk',
            'platform',
            'processing_success',
            'queued',
            'start_date',
            'timestamp',
            'when_processed',
            'when_queued',
        )


class SushiFetchAttemptSimpleSerializer(ModelSerializer):

    counter_version = IntegerField(read_only=True, source='counter_report.counter_version')

    class Meta:
        model = SushiFetchAttempt
        fields = (
            'contains_data',
            'counter_report_id',
            'counter_version',
            'credentials_id',
            'data_file',
            'download_success',
            'end_date',
            'error_code',
            'import_batch',
            'import_crashed',
            'in_progress',
            'is_processed',
            'pk',
            'processing_success',
            'queued',
            'start_date',
            'timestamp',
            'when_processed',
            'when_queued',
        )


class SushiCleanupSerializer(Serializer):
    older_than = DateTimeField(required=False)


class SushiCleanupCountSerializer(Serializer):
    count = IntegerField(required=True)
