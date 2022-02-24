from django.contrib import admin, messages
from django.db.transaction import atomic
from import_export.admin import ExportActionMixin
from import_export.fields import Field
from import_export.resources import ModelResource
from reversion.admin import VersionAdmin

from logs.logic.attempt_import import reprocess_attempt
from logs.models import ImportBatch
from logs.tasks import import_one_sushi_attempt_task
from . import models


class SushiCredentialsResource(ModelResource):
    """
    This is used by django-import-export to facilitate CSV export in Django admin
    """

    platform__name = Field(attribute='platform__name', column_name='platform')
    organization__name = Field(attribute='organization__name', column_name='organization')

    class Meta:
        model = models.SushiCredentials
        fields = (
            'id',
            'title',
            'organization__name',
            'platform__name',
            'url',
            'counter_version',
            'requestor_id',
            'customer_id',
            'http_username',
            'http_password',
            'api_key',
            'extra_params',
            'counter_reports',
        )
        export_order = fields

    def dehydrate_counter_reports(self, credentials: models.SushiCredentials):
        return ', '.join([cr.code for cr in credentials.counter_reports.all()])

    def dehydrate_platform__name(self, credentials: models.SushiCredentials):
        return credentials.platform.name or credentials.platform.short_name

    def dehydrate_organization__name(self, credentials: models.SushiCredentials):
        return credentials.organization.name or credentials.organization.short_name


@admin.register(models.SushiCredentials)
class SushiCredentialsAdmin(ExportActionMixin, VersionAdmin):

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
    list_filter = ['enabled', 'broken', 'counter_version', 'organization', 'platform']
    search_fields = [
        'organization__name',
        'platform__name',
        'pk',
        'url',
    ]
    readonly_fields = ['first_broken_attempt']
    resource_class = SushiCredentialsResource  # for django-import-export

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
    for attempt in queryset.select_for_update(skip_locked=True, of=('self',)):
        if reprocess_attempt(attempt) is not None:
            count += 1
    messages.info(request, f'{count} attempts reimported')


reimport.short_description = 'Reimport data - deletes old and reparses the downloaded file'


def reimport_delayed(modeladmin, request, queryset):
    count = 0
    total_count = queryset.count()
    for attempt in queryset.select_for_update(skip_locked=True, of=('self',)):
        import_one_sushi_attempt_task.delay(attempt.pk, reimport=True)
        count += 1

    already_running_text = (
        f" ({total_count - count} imports already running.)" if total_count != count else ""
    )
    messages.info(request, f'{count} attempts planned to be reimported.{already_running_text}')


reimport_delayed.short_description = 'Plan Reimport data - same as Reimport, but in celery'


@atomic
def delete_with_data(modeladmin, request, queryset):
    del_stats = ImportBatch.objects.filter(
        pk__in=queryset.filter(import_batch__isnull=False).values('import_batch_id')
    ).delete()
    attempts_deleted = queryset.delete()
    batches_deleted = del_stats[1].get('logs.ImportBatch', 0)
    messages.info(
        request, f'{attempts_deleted[0]} attempts deleted with ' f'{batches_deleted} data batches',
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
        'status',
        'error_code',
        'has_import_batch',
    ]
    list_filter = [
        HistoryMode,
        'status',
        'error_code',
        HasImportBatch,
        'counter_report',
        'credentials__organization',
        'credentials__platform',
    ]
    search_fields = [
        'credentials__organization__name',
        'credentials__platform__name',
        'pk',
        'credentials__url',
    ]
    actions = [delete_with_data, reimport, reimport_delayed]
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

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(models.CounterReportsToCredentials)
class CounterReportsToCredentialsAdmin(admin.ModelAdmin):

    list_display = ['credentials', 'counter_report', 'broken']
    list_filter = ['broken', 'counter_report', 'credentials__platform', 'credentials__organization']
    readonly_fields = ['first_broken_attempt', 'credentials', 'counter_report']
