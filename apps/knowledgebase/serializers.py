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
    report_types = serializers.ListField(child=serializers.JSONField())
    counter_registry_id = serializers.UUIDField(allow_null=True)
    url = serializers.URLField(allow_blank=True)
    duplicates = serializers.ListField(
        child=serializers.IntegerField(required=True), allow_empty=True, required=False
    )
    platform_filter = serializers.CharField(allow_null=True, required=False)
    notes_url = serializers.URLField(allow_blank=True, allow_null=True, required=False)


class AttemptOutputSerializer(serializers.Serializer):
    platform_id = serializers.IntegerField()
    counter_version = serializers.IntegerField()
    counter_report_code = serializers.CharField()
    urls = serializers.ListField(child=serializers.URLField())
    latest = serializers.DateField()


class DimensionSerializer(serializers.Serializer):
    pk = serializers.IntegerField(required=True)
    short_name = serializers.CharField(allow_blank=False)
    aliases = serializers.ListField(child=serializers.CharField(allow_blank=False))


class MetricSerializer(serializers.Serializer):
    pk = serializers.IntegerField(required=True)
    short_name = serializers.CharField(allow_blank=False)
    aliases = serializers.ListField(child=serializers.CharField(allow_blank=False))
    interest_group = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ReportTypeSerializer(serializers.Serializer):
    pk = serializers.IntegerField(required=True)
    short_name = serializers.CharField(allow_blank=True, required=True)
    name = serializers.CharField(allow_blank=True)
    metrics = MetricSerializer(many=True)
    dimensions = DimensionSerializer(many=True)
    uses_titles = serializers.BooleanField(allow_null=True, default=None)
    uses_items = serializers.BooleanField(allow_null=True, default=None)


class ParserDefinitionSerializer(serializers.Serializer):
    pk = serializers.IntegerField(required=True)
    parser_name = serializers.CharField(required=True)
    data_format = DataFormat
    areas = serializers.JSONField(required=True)
    platforms = serializers.JSONField(required=True)
    metrics_to_skip = serializers.JSONField(required=True)
    titles_to_skip = serializers.JSONField(required=True)
    dimensions_to_skip = serializers.JSONField(required=True)
    dimensions_validators = serializers.JSONField(required=False)
    metric_aliases = serializers.JSONField(required=True)
    metric_value_extraction_overrides = serializers.JSONField(required=True)
    available_metrics = serializers.JSONField(required=True, allow_null=True)
    dimension_aliases = serializers.JSONField(required=True)
    heuristics = serializers.JSONField(required=True)
    possible_row_offsets = serializers.JSONField(required=True)
    lowest_nibbler_version = serializers.CharField(required=True)
    highest_nibbler_version = serializers.CharField(required=True)
