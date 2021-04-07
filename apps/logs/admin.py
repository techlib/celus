from django.contrib import admin
from modeltranslation.admin import TranslationAdmin

from . import models


@admin.register(models.OrganizationPlatform)
class OrganizationPlatformAdmin(admin.ModelAdmin):

    list_display = ['organization', 'platform']


class IsMaterialized(admin.SimpleListFilter):
    title = 'is materialized'
    parameter_name = 'materialized'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(materialization_spec__isnull=False)
        if self.value() == 'no':
            return queryset.filter(materialization_spec__isnull=True)
        return queryset


@admin.register(models.ReportType)
class ReportTypeAdmin(TranslationAdmin):

    list_display = [
        'short_name',
        'name',
        'desc',
        'dimension_list',
        'source',
        'superseeded_by',
        'materialized',
        'record_count',
    ]
    ordering = ['short_name']
    list_filter = ['source', IsMaterialized, 'default_platform_interest']

    class Media:
        css = {'all': ['css/report_type.css']}

    @classmethod
    def dimension_list(cls, obj: models.ReportType):
        return ', '.join(obj.dimension_short_names)

    def materialized(self, obj: models.ReportType):
        return bool(obj.materialization_spec)

    materialized.boolean = True

    @classmethod
    def record_count(cls, obj: models.ReportType):
        return f'{obj.approx_record_count:,}'


@admin.register(models.Metric)
class MetricAdmin(TranslationAdmin):

    list_display = ['short_name', 'active', 'name']
    list_editable = ['active']
    list_filter = ['active']


@admin.register(models.ReportInterestMetric)
class ReportInterestMetricAdmin(TranslationAdmin):

    list_display = ['report_type', 'metric', 'interest_group', 'target_metric']
    list_filter = ['report_type', 'metric', 'interest_group']
    search_fields = ['report_type__short_name', 'report_type__name', 'metric__name']
    list_select_related = ['report_type', 'metric', 'target_metric', 'interest_group']


@admin.register(models.Dimension)
class DimensionAdmin(TranslationAdmin):

    list_display = ['short_name', 'name', 'type', 'desc', 'source']
    ordering = ['short_name']
    list_filter = ['source']


@admin.register(models.DimensionText)
class DimensionTextAdmin(admin.ModelAdmin):

    list_display = ['id', 'dimension', 'text', 'text_local']
    list_filter = ['dimension']


@admin.register(models.ReportTypeToDimension)
class ReportTypeToDimensionAdmin(admin.ModelAdmin):

    list_display = ['report_type', 'dimension', 'position']
    ordering = ['report_type__short_name', 'position']


@admin.register(models.AccessLog)
class AccessLogAdmin(admin.ModelAdmin):

    list_display = [
        'metric',
        'report_type',
        'organization',
        'platform',
        'target',
        'created',
        'date',
        'value',
    ]
    list_select_related = ['organization', 'platform', 'target', 'metric', 'report_type']
    readonly_fields = ['target', 'import_batch', 'organization', 'platform']
    search_fields = ['platform__name', 'target__name', 'organization__name']
    list_filter = ['report_type', 'organization', 'platform']


@admin.register(models.InterestGroup)
class InterestGroupAdmin(TranslationAdmin):

    list_display = ['short_name', 'important', 'position', 'name']
    list_editable = ['important', 'position']


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


@admin.register(models.ReportMaterializationSpec)
class ReportMaterializationSpecAdmin(admin.ModelAdmin):

    list_display = ['name', 'base_report_type', 'description']


@admin.register(models.FlexibleReport)
class FlexibleReportAdmin(admin.ModelAdmin):

    list_display = ['name', 'access_level', 'owner', 'owner_organization']
