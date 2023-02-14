from django.contrib import admin
from modeltranslation.admin import TranslationAdmin

from . import models


@admin.register(models.ReportDataView)
class ReportDataViewAdmin(TranslationAdmin):

    list_display = [
        'short_name',
        'name',
        'position',
        'is_standard_view',
        'source',
        'filters',
        'metric_allowed_values',
    ]
    list_filter = ['source']
    list_editable = ['position', 'is_standard_view']

    @classmethod
    def filters(cls, obj: models.ReportDataView):
        return '; '.join(
            f'{df.dimension.short_name}: {df.allowed_values}' for df in obj.dimension_filters.all()
        )


@admin.register(models.DimensionFilter)
class DimensionFilterAdmin(admin.ModelAdmin):

    list_display = ['report_data_view', 'dimension', 'allowed_values']
    list_filter = ['report_data_view', 'dimension']


@admin.register(models.ChartDefinition)
class ChartDefinitionAdmin(TranslationAdmin):

    list_display = [
        'name',
        'desc',
        'is_generic',
        'primary_dimension',
        'primary_implicit_dimension',
        'secondary_dimension',
        'secondary_implicit_dimension',
        'chart_type',
    ]


@admin.register(models.ReportViewToChartType)
class ReportViewToChartTypeAdmin(admin.ModelAdmin):

    list_display = ['report_data_view', 'chart_definition', 'position']
    list_editable = ['position']
    list_filter = ['report_data_view', 'chart_definition']
