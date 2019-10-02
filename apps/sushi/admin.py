from django.contrib import admin

from reversion.admin import VersionAdmin

from . import models


@admin.register(models.SushiCredentials)
class SushiCredentialsAdmin(VersionAdmin):

    list_display = ['organization', 'organization_internal_id', 'platform', 'counter_version',
                    'customer_id', 'requestor_id',
                    'enabled']
    list_filter = ['enabled', 'counter_version', 'organization', 'platform']

    @classmethod
    def organization_internal_id(cls, obj: models.SushiCredentials):
        return obj.organization.internal_id


@admin.register(models.CounterReportType)
class CounterReportTypeAdmin(admin.ModelAdmin):

    list_display = ['code', 'name', 'counter_version', 'report_type', 'active', 'superseeded_by']
    list_filter = ['counter_version']


@admin.register(models.SushiFetchAttempt)
class SushiFetchAttemptAdmin(admin.ModelAdmin):

    list_display = ['credentials', 'counter_report', 'timestamp', 'start_date', 'end_date',
                    'queued', 'download_success', 'processing_success', 'is_processed',
                    'contains_data']
    list_filter = ['download_success',  'processing_success', 'is_processed', 'queued',
                   'contains_data', 'counter_report']
    readonly_fields = ['credentials', 'counter_report', 'timestamp', 'start_date', 'end_date',
                       'download_success', 'data_file', 'import_batch', 'queue_previous']
    search_fields = ['credentials__organization__name', 'credentials__platform__name']
