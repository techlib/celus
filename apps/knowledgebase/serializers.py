from rest_framework import serializers


class PlatformSerializer(serializers.Serializer):
    pk = serializers.IntegerField(required=True)
    name = serializers.CharField(allow_blank=True)
    short_name = serializers.CharField(allow_blank=True)
    provider = serializers.CharField(allow_blank=True)
    providers = serializers.ListField(child=serializers.JSONField())
    counter_registry_id = serializers.UUIDField(allow_null=True)
    url = serializers.URLField(allow_blank=True)
