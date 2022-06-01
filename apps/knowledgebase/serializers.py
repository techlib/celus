from rest_framework import serializers


class PlatformSerializer(serializers.Serializer):
    pk = serializers.IntegerField(required=True)
    name = serializers.CharField(allow_blank=True)
    short_name = serializers.CharField(allow_blank=True)
    provider = serializers.CharField(allow_blank=True)
    providers = serializers.ListField(child=serializers.JSONField())
    counter_registry_id = serializers.UUIDField(allow_null=True)
    url = serializers.URLField(allow_blank=True)


class DimensionSerializer(serializers.Serializer):
    pk = serializers.IntegerField(required=True)
    short_name = serializers.CharField(allow_blank=False)
    aliases = serializers.ListField(child=serializers.CharField(allow_blank=False))


class MetricSerializer(serializers.Serializer):
    pk = serializers.IntegerField(required=True)
    short_name = serializers.CharField(allow_blank=False)
    aliases = serializers.ListField(child=serializers.CharField(allow_blank=False))


class ReportTypeSerializer(serializers.Serializer):
    pk = serializers.IntegerField(required=True)
    short_name = serializers.CharField(allow_blank=True, required=True)
    name = serializers.CharField(allow_blank=True)
    metrics = MetricSerializer(many=True)
    dimensions = DimensionSerializer(many=True)
