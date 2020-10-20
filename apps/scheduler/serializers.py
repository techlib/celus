import typing

from rest_framework import serializers

from .models import FetchIntention, Harvest
from sushi.serializers import SushiFetchAttemptSerializer


class StatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    planned = serializers.IntegerField()

    def to_representation(self, instance):
        return {"planned": instance[0], "total": instance[1]}


class CreateFetchIntentionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FetchIntention
        fields = (
            'not_before',
            'credentials',
            'counter_report',
            'start_date',
            'end_date',
            'when_processed',
        )


class FetchIntentionSerializer(serializers.ModelSerializer):
    attempt = SushiFetchAttemptSerializer(required=False)

    class Meta:
        model = FetchIntention
        fields = (
            'not_before',
            'credentials',
            'counter_report',
            'attempt',
            'start_date',
            'end_date',
            'when_processed',
            'data_not_ready_retry',
            'service_not_available_retry',
            'service_busy_retry',
        )


class ListHarvestSerializer(serializers.ModelSerializer):
    intentions = serializers.PrimaryKeyRelatedField(
        source='latest_intentions', many=True, read_only=True
    )
    stats = StatsSerializer()

    class Meta:
        model = Harvest
        fields = (
            'pk',
            'intentions',
            'created',
            'last_updated',
            'last_updated_by',
            'stats',
        )


class RetrieveHarvestSerializer(serializers.ModelSerializer):
    intentions = FetchIntentionSerializer(source="latest_intentions", many=True, read_only=True)
    stats = StatsSerializer()

    class Meta:
        model = Harvest
        fields = (
            'pk',
            'intentions',
            'created',
            'last_updated',
            'last_updated_by',
            'stats',
        )


class CreateHarvestSerializer(serializers.ModelSerializer):
    intentions = FetchIntentionSerializer(many=True, write_only=True)

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
