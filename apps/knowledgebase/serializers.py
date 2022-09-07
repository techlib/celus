from rest_framework import serializers


class DataFormat(serializers.Serializer):
    name = serializers.CharField(required=True)
    id = serializers.IntegerField(required=False)


class PlatformSerializer(serializers.Serializer):
    pk = serializers.IntegerField(required=True)
    name = serializers.CharField(allow_blank=True)
    short_name = serializers.CharField(allow_blank=True)
    provider = serializers.CharField(allow_blank=True)
    providers = serializers.ListField(child=serializers.JSONField())
    counter_registry_id = serializers.UUIDField(allow_null=True)
    url = serializers.URLField(allow_blank=True)
    duplicates = serializers.ListField(
        child=serializers.IntegerField(required=True), allow_empty=True, required=False,
    )


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


class ParserDefinitionSerializer(serializers.Serializer):
    pk = serializers.IntegerField(required=True)
    parser_name = serializers.CharField(required=True)
    data_format = DataFormat
    areas = serializers.JSONField(required=True)
    platforms = serializers.JSONField(required=True)
    metrics_to_skip = serializers.JSONField(required=True)
    titles_to_skip = serializers.JSONField(required=True)
    dimensions_to_skip = serializers.JSONField(required=True)
    metric_aliases = serializers.JSONField(required=True)
    dimension_aliases = serializers.JSONField(required=True)
    heuristics = serializers.JSONField(required=True)
