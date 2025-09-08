from core.validators import month_validator
from logs.serializers import DimensionSerializer
from rest_framework.fields import BooleanField, CharField, IntegerField, ListField
from rest_framework.serializers import ModelSerializer, Serializer

from .models import ChartDefinition, DimensionFilter, ReportDataView, ReportViewToChartType


class DimensionFilterSerializer(ModelSerializer):
    dimension = DimensionSerializer(read_only=True)
    allowed_value_ids = ListField(child=IntegerField(), read_only=True)

    class Meta:
        model = DimensionFilter
        fields = ("dimension", "allowed_values", "allowed_value_ids")


class ReportDataViewSerializer(ModelSerializer):
    public = BooleanField(default=False)
    is_proxy = BooleanField(read_only=True, default=False)
    is_interest = BooleanField(read_only=True)
    counter_version = CharField(read_only=True, required=False)

    class Meta:
        model = ReportDataView
        fields = (
            "pk",
            "short_name",
            "name",
            "name_cs",
            "name_en",
            "desc",
            "public",
            "is_interest",
            "counter_version",
            "is_standard_view",
            "position",
            "is_proxy",
        )


class ReportDataViewFullSerializer(ReportDataViewSerializer):
    dimension_filters = DimensionFilterSerializer(many=True, read_only=True)
    metric_allowed_value_ids = ListField(child=IntegerField(), read_only=True)

    class Meta(ReportDataViewSerializer.Meta):
        fields = ReportDataViewSerializer.Meta.fields + (
            "metric_allowed_values",
            "metric_allowed_value_ids",
            "dimension_filters",
        )


class ChartDefinitionSerializer(ModelSerializer):
    primary_dimension = DimensionSerializer(read_only=True)
    secondary_dimension = DimensionSerializer(read_only=True)

    class Meta:
        model = ChartDefinition
        fields = (
            "pk",
            "name",
            "desc",
            "primary_dimension",
            "primary_implicit_dimension",
            "secondary_dimension",
            "secondary_implicit_dimension",
            "chart_type",
            "ordering",
            "ignore_organization",
            "ignore_platform",
            "scope",
        )


class ReportViewToChartTypeSerializer(ModelSerializer):
    class Meta:
        model = ReportViewToChartType
        fields = ("pk", "report_data_view", "chart_definition", "position")


class ReportingUrlSerializer(Serializer):
    primary_dimension = CharField(required=True)
    secondary_dimension = CharField(required=False)
    title = IntegerField(required=False)
    organization = IntegerField(required=False)
    platform = IntegerField(required=False)
    start_date = CharField(validators=[month_validator], required=False)
    end_date = CharField(validators=[month_validator], required=False)
    metric = IntegerField(required=False)
    end_date = CharField(validators=[month_validator], required=False)
