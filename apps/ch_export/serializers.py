from rest_framework import serializers

from .models import AccessLogExport


class AccessLogExportSerializer(serializers.ModelSerializer):
    organization = serializers.CharField(source="organization.name", read_only=True)
    status = serializers.SerializerMethodField()
    last_sync = serializers.SerializerMethodField()

    class Meta:
        model = AccessLogExport
        fields = ["id", "organization", "status", "last_sync", "ch_database", "ch_password"]
        read_only_fields = fields

    def get_status(self, obj):
        latest_batch = obj.latest_batch()
        if not latest_batch:
            return None
        return latest_batch.get_status()

    def get_last_sync(self, obj):
        latest_batch = obj.latest_batch()
        if latest_batch:
            return latest_batch.created
        return None
