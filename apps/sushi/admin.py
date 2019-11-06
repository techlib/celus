from django.contrib import admin, messages

from reversion.admin import VersionAdmin

from logs.logic.attempt_import import reprocess_attempt
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

    list_display = ['code', 'name', 'counter_version', 'report_type', 'active']
    list_filter = ['counter_version']
    ordering = ['code']


def reimport(modeladmin, request, queryset):
    count = 0
    for attempt in queryset:  # type: models.SushiFetchAttempt
        reprocess_attempt(attempt)
        count += 1
    messages.info(request, f'{count} attempts reimported')


reimport.short_description = 'Reimport data - deletes old and reparses the downloaded file'


@admin.register(models.SushiFetchAttempt)
class SushiFetchAttemptAdmin(admin.ModelAdmin):

    list_display = ['organization', 'platform', 'counter_version', 'report', 'timestamp',
                    'start_date', 'end_date',
                    'queued', 'import_crashed', 'download_success', 'processing_success',
                    'is_processed', 'contains_data', 'error_code']
    list_filter = ['download_success',  'processing_success', 'is_processed', 'queued',
                   'error_code',
                   'contains_data', 'counter_report']
    readonly_fields = ['credentials', 'counter_report', 'timestamp', 'start_date', 'end_date',
                       'download_success', 'data_file', 'import_batch', 'queue_previous']
    search_fields = ['credentials__organization__name', 'credentials__platform__name']
    actions = [reimport]
    list_select_related = ['credentials__platform', 'credentials__organization', 'credentials',
                           'counter_report']

    def report(self, obj: models.SushiFetchAttempt):
        return obj.counter_report.code

    def organization(self, obj: models.SushiFetchAttempt):
        return obj.credentials.organization

    def platform(self, obj: models.SushiFetchAttempt):
        return obj.credentials.platform

    def counter_version(self, obj: models.SushiFetchAttempt):
        return obj.credentials.counter_version
