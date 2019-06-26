from django.contrib import admin

from . import models


@admin.register(models.OrganizationPlatform)
class OrganizationPlatformAdmin(admin.ModelAdmin):

    list_display = ['organization', 'platform']


@admin.register(models.ReportType)
class ReportTypeAdmin(admin.ModelAdmin):

    list_display = ['short_name', 'name', 'desc']


@admin.register(models.Metric)
class MetricAdmin(admin.ModelAdmin):

    list_display = ['short_name', 'name', 'desc']


@admin.register(models.Dimension)
class DimensionAdmin(admin.ModelAdmin):

    list_display = ['short_name', 'name', 'type', 'desc']


@admin.register(models.DimensionText)
class DimensionTextAdmin(admin.ModelAdmin):

    list_display = ['id', 'dimension', 'text', 'text_local']


@admin.register(models.ReportTypeToDimension)
class ReportTypeToDimensionAdmin(admin.ModelAdmin):

    list_display = ['report_type', 'dimension', 'position']


@admin.register(models.AccessLog)
class AccessLogAdmin(admin.ModelAdmin):

    list_display = ['metric', 'report_type', 'source', 'target']
