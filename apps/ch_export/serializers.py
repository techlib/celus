from functools import lru_cache

from rest_framework import serializers

from .models import AccessLogExport, AccessLogExportBatch


class AccessLogExportBatchSerializer(serializers.ModelSerializer):
    report_types = serializers.SerializerMethodField()

    class Meta:
        model = AccessLogExportBatch
        fields = ["id", "created", "report_types"]

    def get_report_types(self, obj):
        return list(
            obj.tasks.order_by("report_type__short_name").values_list(
                "report_type__short_name", flat=True
            )
        )


class AccessLogExportSerializer(serializers.ModelSerializer):
    organization = serializers.CharField(source="organization.name", read_only=True)
    status = serializers.SerializerMethodField()
    last_sync = serializers.SerializerMethodField()
    latest_batch = AccessLogExportBatchSerializer(read_only=True)

    class Meta:
        model = AccessLogExport
        fields = [
            "id",
            "organization",
            "status",
            "last_sync",
            "ch_database",
            "ch_password",
            "latest_batch",
        ]
        read_only_fields = fields

    @lru_cache(maxsize=100)  # noqa: B019 - no problem with caching here
    def get_latest_batch(self, obj):
        return obj.latest_batch()

    def get_status(self, obj):
        if latest_batch := self.get_latest_batch(obj):
            return latest_batch.get_status()
        return None

    def get_last_sync(self, obj):
        if latest_batch := self.get_latest_batch(obj):
            return latest_batch.created
        return None
