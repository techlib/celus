from django.contrib import admin

from . import models


@admin.register(models.SushiCredentials)
class SushiCredentialsAdmin(admin.ModelAdmin):

    list_display = ['organization', 'organization_internal_id', 'platform', 'counter_version',
                    'customer_id', 'requestor_id',
                    'enabled']
    list_filter = ['enabled', 'counter_version', 'organization', 'platform']

    @classmethod
    def organization_internal_id(cls, obj: models.SushiCredentials):
        return obj.organization.internal_id


@admin.register(models.CounterReportType)
class CounterReportTypeAdmin(admin.ModelAdmin):

    list_display = ['code', 'name', 'counter_version', 'report_type']
    list_filter = ['counter_version']


@admin.register(models.SushiFetchAttempt)
class SushiFetchAttemptAdmin(admin.ModelAdmin):

    list_display = ['credentials', 'counter_report', 'timestamp', 'start_date', 'end_date',
                    'queued', 'success', 'is_processed']
    list_filter = ['success', 'is_processed', 'queued', 'counter_report']
    readonly_fields = ['credentials', 'counter_report', 'timestamp', 'start_date', 'end_date',
                       'success', 'data_file']
    search_fields = ['credentials__organization__name', 'credentials__platform__name']
