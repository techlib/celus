from rest_framework import serializers as s


class ReportDataSourceSerializer(s.Serializer):

    id = s.CharField()
    name = s.CharField()
    reportType = s.CharField(source='report_type')
    metric = s.CharField()
    filters = s.DictField()
    fallbackFor = s.CharField(source='fallback_for')


class ReportPartStageSerializer(s.Serializer):

    id = s.CharField()
    name = s.CharField()
    description = s.CharField()
    formula = s.CharField()
    usedDataSources = s.ListField(source='get_used_data_sources')


class ReportPartSerializer(s.Serializer):

    name = s.CharField()
    description = s.CharField()
    explanation = s.CharField()
    stages = ReportPartStageSerializer(many=True)
    implementationNote = s.CharField(source='implementation_note')


class ReportSerializer(s.Serializer):

    name = s.CharField()
    description = s.CharField()
    parts = ReportPartSerializer(many=True)
    dataSources = ReportDataSourceSerializer(source='sorted_sources', many=True)
    infoUrl = s.URLField(source='info_url')
