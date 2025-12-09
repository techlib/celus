from functools import lru_cache
from typing import Optional

from rest_framework import serializers

from .models import AccessLogExport, AccessLogExportBatch, AccessLogExportTask


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
    can_start_export = serializers.SerializerMethodField()
    next_export_available_at = serializers.SerializerMethodField()

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
            "can_start_export",
            "next_export_available_at",
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

    def get_can_start_export(self, obj):
        request = self.context.get("request")
        if not request or not request.user:
            return False
        return obj.can_start_export(request.user)

    def get_next_export_available_at(self, obj):
        request = self.context.get("request")
        if not request or not request.user:
            return None
        if next_available := obj.get_next_export_available_at(request.user):
            return next_available.isoformat()
        return None


class AccessLogExportTaskSerializer(serializers.ModelSerializer):
    report_type = serializers.CharField(source="report_type.short_name", read_only=True)
    eta = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = AccessLogExportTask
        fields = [
            "id",
            "report_type",
            "started",
            "finished",
            "error",
            "progress_current",
            "progress_total",
            "eta",
            "status",
        ]
        read_only_fields = fields

    def get_eta(self, obj) -> Optional[str]:
        eta = obj.eta
        if eta is None:
            return None
        return str(eta).split(".")[0]  # Format as HH:MM:SS

    def get_status(self, obj) -> str:
        if obj.error:
            return "failed"
        if obj.finished:
            return "completed"
        if obj.started:
            return "running"
        return "pending"


class AccessLogExportBatchProgressSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    tasks = AccessLogExportTaskSerializer(many=True, read_only=True)

    class Meta:
        model = AccessLogExportBatch
        fields = ["id", "created", "status", "tasks"]
        read_only_fields = fields

    def get_status(self, obj) -> str:
        return obj.get_status()
