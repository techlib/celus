from django.contrib import admin
from django.db.models import Count

from . import models


@admin.register(models.OrganizationPlatform)
class OrganizationPlatformAdmin(admin.ModelAdmin):

    list_display = ['organization', 'platform']


@admin.register(models.ReportType)
class ReportTypeAdmin(admin.ModelAdmin):

    list_display = ['short_name', 'name', 'desc', 'dimension_list', 'source']
    ordering = ['short_name']

    @classmethod
    def dimension_list(cls, obj: models.ReportType):
        return ', '.join(obj.dimension_short_names)


@admin.register(models.Metric)
class MetricAdmin(admin.ModelAdmin):

    list_display = ['short_name', 'active', 'name', 'interest_group', 'name_in_interest_group']
    list_editable = ['active']


@admin.register(models.Dimension)
class DimensionAdmin(admin.ModelAdmin):

    list_display = ['short_name', 'name', 'type', 'desc']
    ordering = ['short_name']


@admin.register(models.DimensionText)
class DimensionTextAdmin(admin.ModelAdmin):

    list_display = ['id', 'dimension', 'text', 'text_local']


@admin.register(models.ReportTypeToDimension)
class ReportTypeToDimensionAdmin(admin.ModelAdmin):

    list_display = ['report_type', 'dimension', 'position']
    ordering = ['report_type__short_name', 'position']


@admin.register(models.AccessLog)
class AccessLogAdmin(admin.ModelAdmin):

    list_display = ['metric', 'report_type', 'organization', 'platform', 'target', 'created',
                    'date', 'value']
    list_select_related = ['organization', 'platform', 'target', 'metric', 'report_type']
    readonly_fields = ['target', 'import_batch', 'organization', 'platform']
    search_fields = ['platform__name', 'target__name', 'organization__name']
    list_filter = ['report_type', 'organization', 'platform']


@admin.register(models.InterestGroup)
class InterestGroupAdmin(admin.ModelAdmin):

    list_display = ['short_name', 'name']


@admin.register(models.ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):

    list_display = ['created', 'report_type', 'organization', 'platform', 'user', 'log_count']
    list_filter = ['report_type', 'organization', 'platform']
    list_select_related = ['report_type', 'organization', 'platform']

    @classmethod
    def log_count(cls, obj: models.ImportBatch):
        return obj.accesslog_set.count()

    # the following is actually much slower than doing a separate query for each import batch
    # def get_queryset(self, request):
    #     qs = super().get_queryset(request)
    #     return qs.annotate(log_count=Count('accesslog'))

