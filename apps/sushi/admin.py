from django.contrib import admin, messages
from django.db.transaction import atomic

from reversion.admin import VersionAdmin

from logs.logic.attempt_import import reprocess_attempt
from logs.models import ImportBatch
from . import models


@admin.register(models.SushiCredentials)
class SushiCredentialsAdmin(VersionAdmin):

    list_display = [
        'organization',
        'organization_internal_id',
        'platform',
        'url',
        'counter_version',
        'customer_id',
        'requestor_id',
        'enabled',
    ]
    list_filter = ['enabled', 'counter_version', 'organization', 'platform']
    search_fields = [
        'organization__name',
        'platform__name',
        'pk',
        'url',
    ]

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


@atomic
def delete_with_data(modeladmin, request, queryset):
    batches_deleted = ImportBatch.objects.filter(
        pk__in=queryset.filter(import_batch__isnull=False).values('import_batch_id')
    ).delete()
    attempts_deleted = queryset.delete()
    messages.info(
        request,
        f'{attempts_deleted[0]} attempts deleted with ' f'{batches_deleted[0]} data batches',
    )


delete_with_data.short_description = 'Delete selected attempts including related usage data'


class HasImportBatch(admin.SimpleListFilter):
    title = 'has import batch'
    parameter_name = 'has'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(import_batch__isnull=False)
        if self.value() == 'no':
            return queryset.filter(import_batch__isnull=True)
        return queryset


class HistoryMode(admin.SimpleListFilter):
    title = 'history mode'
    parameter_name = 'hm'

    def lookups(self, request, model_admin):
        return (
            ('current', 'Current only'),
            ('current_and_success', 'Current and sucessful'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'current':
            return queryset.current()
        if self.value() == 'current_and_success':
            return queryset.current_or_successful()
        return queryset


@admin.register(models.SushiFetchAttempt)
class SushiFetchAttemptAdmin(admin.ModelAdmin):

    list_display = [
        'organization',
        'platform',
        'counter_version',
        'report',
        'timestamp',
        'start_date',
        'end_date',
        'queued',
        'download_success',
        'processing_success',
        'contains_data',
        'import_crashed',
        'is_processed',
        'error_code',
        'has_import_batch',
    ]
    list_filter = [
        HistoryMode,
        'download_success',
        'processing_success',
        'is_processed',
        'queued',
        'import_crashed',
        'error_code',
        'contains_data',
        HasImportBatch,
        'counter_report',
        'credentials__organization',
        'credentials__platform',
    ]
    readonly_fields = [
        'credentials',
        'counter_report',
        'timestamp',
        'start_date',
        'end_date',
        'download_success',
        'data_file',
        'import_batch',
        'queue_previous',
        'queueing_explanation',
    ]
    search_fields = [
        'credentials__organization__name',
        'credentials__platform__name',
        'pk',
        'credentials__url',
    ]
    actions = [delete_with_data, reimport]
    list_select_related = [
        'credentials__platform',
        'credentials__organization',
        'credentials',
        'counter_report',
        'import_batch',
    ]

    class Media:
        css = {"all": ("admin/admin.css",)}

    def report(self, obj: models.SushiFetchAttempt):
        return obj.counter_report.code

    def organization(self, obj: models.SushiFetchAttempt):
        return obj.credentials.organization

    def platform(self, obj: models.SushiFetchAttempt):
        return obj.credentials.platform

    def counter_version(self, obj: models.SushiFetchAttempt):
        return obj.credentials.counter_version

    def has_import_batch(self, obj: models.SushiFetchAttempt):
        return obj.import_batch is not None

    has_import_batch.boolean = True
