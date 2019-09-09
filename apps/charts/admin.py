from django.contrib import admin

from . import models


@admin.register(models.ReportDataView)
class ReportDataViewAdmin(admin.ModelAdmin):

    list_display = ['short_name', 'name', 'source', 'primary_dimension', 'filters',
                    'metric_allowed_values']
    ordering = ['short_name']
    list_filter = ['source']

    @classmethod
    def filters(cls, obj: models.ReportDataView):
        return '; '.join(f'{df.dimension.short_name}: {df.allowed_values}'
                         for df in obj.dimension_filters.all())


@admin.register(models.DimensionFilter)
class DimensionFilterAdmin(admin.ModelAdmin):

    list_display = ['report_data_view', 'dimension', 'allowed_values']
