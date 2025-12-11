from rest_framework import serializers as s


class ReportDataSourceSerializer(s.Serializer):
    id = s.CharField()
    name = s.CharField()
    reportType = s.CharField(source="report_type")
    metric = s.CharField()
    filters = s.DictField()
    fallbackFor = s.CharField(source="fallback_for")


class ReportPartStageSerializer(s.Serializer):
    id = s.CharField()
    name = s.CharField()
    description = s.CharField()
    formula = s.CharField()
    usedDataSources = s.ListField(source="get_used_data_sources")


class ReportPartSerializer(s.Serializer):
    name = s.CharField()
    description = s.CharField()
    explanation = s.CharField()
    stages = ReportPartStageSerializer(many=True)
    implementationNote = s.CharField(source="implementation_note")


class ReportSerializer(s.Serializer):
    id = s.CharField()  # id is derived from the YAML file name
    name = s.CharField()
    description = s.CharField()
    generalInfo = s.CharField(source="general_info")
    parts = ReportPartSerializer(many=True)
    dataSources = ReportDataSourceSerializer(source="sorted_sources", many=True)
    infoUrl = s.URLField(source="info_url")


class AnomalyDetailsSerializer(s.Serializer):
    reasons = s.ListField(child=s.DictField())


class AnomalySerializer(s.Serializer):
    class PlatformInlineSerializer(s.Serializer):
        id = s.IntegerField(source="platform_id")
        name = s.CharField(source="platform_name")
        short_name = s.CharField(source="platform_short_name")

    class ReportTypeInlineSerializer(s.Serializer):
        id = s.IntegerField(source="report_type_id")
        short_name = s.CharField(source="report_type_short_name")
        name = s.CharField(source="report_type_name")

    id = s.IntegerField()
    date = s.DateField()
    # Compact nested platform object, built from CH fields
    platform = PlatformInlineSerializer(source="*")
    organization = s.CharField()
    reportType = ReportTypeInlineSerializer(source="*")
    metric = s.CharField()
    value = s.IntegerField()
    differenceFromMedian = s.IntegerField(source="median_diff")
    significance = s.IntegerField()
    # For plotting
    median = s.IntegerField()
    lowerBound = s.IntegerField(source="lower_bound")
    upperBound = s.IntegerField(source="upper_bound")
    history = s.DictField(child=s.IntegerField())
    # IDs to allow linking into reporting
    organizationId = s.IntegerField(source="organization_id")
    metricId = s.IntegerField(source="metric_id")
