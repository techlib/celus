from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.fields import (
    BooleanField,
    CurrentUserDefault,
    ChoiceField,
    CharField,
    DateTimeField,
    DateField,
    HiddenField,
    IntegerField,
    SerializerMethodField,
    ReadOnlyField,
)
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.serializers import (
    ModelSerializer,
    Serializer,
    ValidationError,
    SlugRelatedField,
)


from core.logic.dates import month_end
from core.models import UL_CONS_STAFF
from organizations.models import Organization
from organizations.serializers import OrganizationSerializer
from publications.models import Platform
from publications.serializers import PlatformSerializer, SimplePlatformSerializer
from .models import (
    COUNTER_REPORTS,
    SushiCredentials,
    CounterReportType,
    SushiFetchAttempt,
    CounterReportsToCredentials,
)


class UnsetBrokenSerializer(Serializer):
    counter_reports = SlugRelatedField(
        queryset=CounterReportType.objects, many=True, slug_field='code', required=False
    )

    class Meta:
        model = SushiCredentials
        fields = ('counter_reports',)


class CounterReportTypeSerializer(ModelSerializer):
    class Meta:
        model = CounterReportType
        fields = ('id', 'code', 'name', 'counter_version')


class CounterReportsToCredentialsSerializer(ModelSerializer):

    id = ReadOnlyField(source='counter_report_id')
    code = ReadOnlyField(source='counter_report.code')
    name = ReadOnlyField(source='counter_report.name')
    counter_version = ReadOnlyField(source='counter_report.counter_version')

    class Meta:
        model = CounterReportsToCredentials
        fields = ('id', 'code', 'name', 'counter_version', 'broken')


class SushiCredentialsSerializer(ModelSerializer):

    organization = OrganizationSerializer(read_only=True)
    platform = PlatformSerializer(read_only=True)
    counter_reports = PrimaryKeyRelatedField(
        queryset=CounterReportType.objects.all(), many=True, read_only=False, write_only=True,
    )

    counter_reports_long = CounterReportsToCredentialsSerializer(
        many=True, source='counterreportstocredentials_set', read_only=True
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
            'counter_reports',
            'counter_reports_long',
            'organization_id',
            'platform_id',
            'submitter',
            'locked_for_me',
            'lock_level',
            'can_lock',
            'locked',
            'outside_consortium',
            'broken',
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


class SushiCredentialsDataCounterReportSerializer(Serializer):
    id = IntegerField(required=True)
    code = ChoiceField(choices=[e[0] for e in COUNTER_REPORTS], required=True)
    name = CharField(allow_blank=True)


class SushiCredentialsDataReportSerializer(Serializer):
    status = ChoiceField(
        choices=('success', 'no_data', 'failed', 'untried', 'partial_data'), required=True
    )
    planned = BooleanField(required=True)
    broken = BooleanField()
    counter_report = SushiCredentialsDataCounterReportSerializer()


class SushiCredentialsDataSerializer(Serializer):
    year = IntegerField(required=True, max_value=3000, min_value=1970)
    for month in range(1, 13):
        locals()[f"{month:02d}"] = SushiCredentialsDataReportSerializer(many=True)


class SushiFetchAttemptSerializer(ModelSerializer):
    class Meta:
        model = SushiFetchAttempt
        fields = (
            'counter_report',
            'credentials',
            'data_file',
            'end_date',
            'error_code',
            'import_batch',
            'log',
            'organization',
            'pk',
            'platform',
            'start_date',
            'timestamp',
            'when_processed',
            'partial_data',
            'status',
        )


class SushiFetchAttemptSimpleSerializer(ModelSerializer):

    counter_version = IntegerField(read_only=True, source='counter_report.counter_version')

    class Meta:
        model = SushiFetchAttempt
        fields = (
            'counter_report_id',
            'counter_version',
            'credentials_id',
            'data_file',
            'end_date',
            'error_code',
            'import_batch',
            'pk',
            'start_date',
            'timestamp',
            'when_processed',
            'status',
        )


class SushiFetchAttemptFlatSerializer(ModelSerializer):
    class Meta:
        model = SushiFetchAttempt
        fields = (
            'counter_report',
            'credentials',
            'data_file',
            'end_date',
            'error_code',
            'import_batch',
            'log',
            'pk',
            'start_date',
            'timestamp',
            'when_processed',
            'partial_data',
            'status',
        )


class SushiCleanupSerializer(Serializer):
    older_than = DateTimeField(required=False)
