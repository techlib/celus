from organizations.serializers import OrganizationSerializer, OrganizationShortSerializer
from publications.serializers import PlatformSerializer, SimplePlatformSerializer
from rest_framework import serializers
from rest_framework.fields import DateField, DateTimeField
from sushi.serializers import (
    CounterReportTypeSerializer,
    SushiFetchAttemptFlatSerializer,
    SushiFetchAttemptSimpleSerializer,
)

from .models import Automatic, FetchIntention, Harvest


class StatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    planned = serializers.IntegerField()
    attempt_count = serializers.IntegerField()
    working = serializers.IntegerField()

    def to_representation(self, instance):
        return {
            k: v
            for k, v in instance.items()
            if k in ("planned", "total", "attempt_count", "working")
        }


class CreateFetchIntentionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FetchIntention
        fields = ('not_before', 'credentials', 'counter_report', 'start_date', 'end_date')


class DuplicateFetchIntentionSerializer(serializers.ModelSerializer):
    attempt = SushiFetchAttemptFlatSerializer(required=True)  # duplicate should have data

    class Meta:
        model = FetchIntention
        fields = (
            'pk',
            'not_before',
            'credentials',
            'counter_report',
            'platform_name',
            'organization_name',
            'counter_report_code',
            'attempt',
            'start_date',
            'end_date',
            'when_processed',
        )


class FetchIntentionSerializer(serializers.ModelSerializer):
    attempt = SushiFetchAttemptFlatSerializer(required=False)
    fetching_data = serializers.BooleanField()
    duplicate_of = DuplicateFetchIntentionSerializer(required=False)
    previous_intention = DuplicateFetchIntentionSerializer(required=False)
    counter_report_verbose = CounterReportTypeSerializer(read_only=True, source='counter_report')
    platform = SimplePlatformSerializer(read_only=True, source='credentials.platform')
    organization = OrganizationSerializer(read_only=True, source='credentials.organization')

    class Meta:
        model = FetchIntention
        fields = (
            'pk',
            'not_before',
            'broken_credentials',
            'credentials',
            'counter_report',
            'counter_report_verbose',
            'platform',
            'organization',
            'counter_report_code',
            'fetching_data',
            'attempt',
            'start_date',
            'end_date',
            'when_processed',
            'data_not_ready_retry',
            'service_not_available_retry',
            'service_busy_retry',
            'duplicate_of',
            'previous_intention',
            'canceled',
        )


class AutomaticInHarvestSerializer(serializers.ModelSerializer):
    organization = OrganizationSerializer()

    class Meta:
        model = Automatic
        fields = ('pk', 'month', 'organization')


class DetailHarvestSerializer(serializers.ModelSerializer):
    intentions = serializers.PrimaryKeyRelatedField(
        source='latest_intentions', many=True, read_only=True
    )
    stats = StatsSerializer()
    organizations = OrganizationSerializer(many=True, read_only=True)
    platforms = PlatformSerializer(many=True, read_only=True)
    last_attempt_date = DateTimeField(read_only=True)
    automatic = AutomaticInHarvestSerializer()

    class Meta:
        model = Harvest
        fields = (
            'pk',
            'intentions',
            'created',
            'last_updated',
            'last_updated_by',
            'stats',
            'automatic',
            'organizations',
            'platforms',
            'last_attempt_date',
        )


class ListHarvestSerializer(serializers.ModelSerializer):
    stats = StatsSerializer()
    organizations = OrganizationShortSerializer(many=True, read_only=True)
    platforms = SimplePlatformSerializer(many=True, read_only=True)
    last_attempt_date = DateTimeField(read_only=True)
    automatic = AutomaticInHarvestSerializer()
    start_date = DateField()
    end_date = DateField()
    last_processed = DateTimeField()
    broken = serializers.IntegerField()

    class Meta:
        model = Harvest
        fields = (
            'pk',
            'created',
            'stats',
            'automatic',
            'organizations',
            'platforms',
            'last_attempt_date',
            'start_date',
            'end_date',
            'last_processed',
            'broken',
        )


class CreateHarvestSerializer(serializers.ModelSerializer):
    intentions = CreateFetchIntentionSerializer(many=True, write_only=True)

    class Meta:
        model = Harvest
        fields = ('intentions',)

    def create(self, validated_data):
        intentions = validated_data.pop('intentions', [])

        created_intentions = [FetchIntention(**intention) for intention in intentions]

        return Harvest.plan_harvesting(
            intentions=created_intentions,
            priority=FetchIntention.PRIORITY_NOW,
            user=validated_data.get("last_updated_by"),
        )

    def validate_intentions(self, items):
        if len(items) == 0:
            raise serializers.ValidationError("At least one intention has to be used")
        return items


class MonthOverviewSerializer(serializers.ModelSerializer):
    attempt = SushiFetchAttemptSimpleSerializer()
    counter_version = serializers.IntegerField(
        read_only=True, source='counter_report.counter_version'
    )
    data_file = serializers.CharField(read_only=True, source='attempt.data_file')
    error_code = serializers.CharField(read_only=True, source='attempt.error_code')
    import_batch = serializers.PrimaryKeyRelatedField(read_only=True, source='attempt.import_batch')
    status = serializers.CharField(read_only=True, source='attempt.status')
    when_processed = DateTimeField(read_only=True, source='attempt.when_processed')
    when_downloaded = DateTimeField(read_only=True, source='when_processed')

    class Meta:
        model = FetchIntention
        fields = (
            'attempt',
            'counter_report_id',
            'counter_version',
            'credentials_id',
            'data_file',
            'start_date',
            'end_date',
            'error_code',
            'import_batch',
            'pk',
            'when_processed',
            'when_downloaded',
            'status',
        )
