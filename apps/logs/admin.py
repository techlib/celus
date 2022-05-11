from django import forms
from django.contrib import admin, messages
from django.contrib.admin import widgets, TabularInline
from django.db.models import Count
from django.utils.translation import ngettext
from modeltranslation.admin import TranslationAdmin

from . import models
from .models import ReportInterestMetric, MduState
from .tasks import reprocess_mdu_task, import_manual_upload_data


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


class ReportInterestMetricInline(TabularInline):
    model = ReportInterestMetric
    fields = ['metric', 'interest_group', 'target_metric']


class ReportTypeForm(forms.ModelForm):
    controlled_metrics = forms.ModelMultipleChoiceField(
        queryset=models.Metric.objects.all(),
        widget=widgets.FilteredSelectMultiple("Controlled metrics", is_stacked=False),
        required=False,
    )

    class Meta:
        model = models.ReportType
        fields = '__all__'


@admin.register(models.ReportType)
class ReportTypeAdmin(TranslationAdmin):
    form = ReportTypeForm

    list_display = [
        'short_name',
        'name',
        'dimension_list',
        'source',
        'superseeded_by',
        'materialized',
        'rim_count',
        'cm_count',
        'record_count',
    ]
    ordering = ['short_name']
    list_filter = ['source', IsMaterialized, 'default_platform_interest']
    readonly_fields = ['approx_record_count']
    inlines = [ReportInterestMetricInline]
    list_select_related = ['source__organization']

    class Media:
        css = {'all': ['css/report_type.css']}

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                rim_count=Count('reportinterestmetric__metric', distinct=True),
                cm_count=Count('controlled_metrics', distinct=True),
            )
        )

    def rim_count(self, obj: models.ReportType):
        return obj.rim_count

    rim_count.short_description = 'interest metrics'

    def cm_count(self, obj: models.ReportType):
        return obj.cm_count

    cm_count.short_description = 'controlled metrics'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == 'source':
            field.queryset = field.queryset.select_related('organization')
        return field

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

    list_display = ['short_name', 'active', 'name', 'controlled_report_types']
    list_editable = ['active']
    list_filter = ['active']

    @classmethod
    def controlled_report_types(cls, obj: models.Metric):
        return ', '.join(str(e) for e in obj.controlled.all())

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('controlled')


@admin.register(models.ReportInterestMetric)
class ReportInterestMetricAdmin(TranslationAdmin):

    list_display = ['report_type', 'metric', 'interest_group', 'target_metric']
    list_filter = ['report_type', 'metric', 'interest_group']
    search_fields = ['report_type__short_name', 'report_type__name', 'metric__name']
    list_select_related = ['report_type', 'metric', 'target_metric', 'interest_group']


@admin.register(models.Dimension)
class DimensionAdmin(TranslationAdmin):

    list_display = ['short_name', 'name', 'desc', 'source']
    ordering = ['short_name']
    list_filter = ['source']


@admin.register(models.DimensionText)
class DimensionTextAdmin(TranslationAdmin):

    list_display = ['id', 'dimension', 'text', 'text_local']
    list_filter = ['dimension']


@admin.register(models.ReportTypeToDimension)
class ReportTypeToDimensionAdmin(admin.ModelAdmin):

    list_display = ['report_type', 'dimension', 'position']
    ordering = ['report_type__short_name', 'position']
    list_filter = ['report_type', 'dimension']


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
            return queryset.filter(import_batches__isnull=False)
        if self.value() == 'no':
            return queryset.filter(import_batches__isnull=True)
        return queryset


@admin.register(models.ManualDataUpload)
class ManualDataUploadAdmin(admin.ModelAdmin):

    list_filter = ['state', 'report_type', 'organization', 'platform', HasImportBatch]
    list_display = ['created', 'report_type', 'platform', 'organization', 'user', 'state']
    list_select_related = ['report_type', 'organization', 'platform', 'user']
    readonly_fields = [
        'data_file',
        'created',
    ]
    search_fields = [
        'organization__name',
        'platform__name',
        'pk',
        'user__username',
        'user__email',
    ]
    actions = ['regenerate_preflight', 'reimport']

    @admin.action(description="Regenerate preflight data")
    def regenerate_preflight(self, request, queryset):
        count = 0
        for mdu in queryset:
            if mdu.regenerate_preflight():
                count += 1

        self.message_user(
            request,
            ngettext(
                "%d preflight started to regenerate", "%d preflights started to regenerate", count
            )
            % count,
            messages.SUCCESS,
        )

    @admin.action(
        description="Reimport data - deletes old and re-imports the file again. "
        "Runs in the background"
    )
    def reimport(self, request, queryset):
        count = 0
        total_count = queryset.count()
        for mdu in queryset.select_for_update(skip_locked=True, of=('self',)):
            mdu.unprocess()
            # import_manual_upload_data does not work without the state being `IMPORTING`
            mdu.state = MduState.IMPORTING
            mdu.save()
            import_manual_upload_data.apply_async(args=(mdu.pk, mdu.user_id), countdown=2)
            count += 1

        already_running_text = (
            f" ({total_count - count} imports already running.)" if total_count != count else ""
        )
        messages.info(
            request,
            f'{count} uploads planned to be reimported.{already_running_text}',
            messages.SUCCESS,
        )


@admin.register(models.LastAction)
class LastActionAdmin(admin.ModelAdmin):

    list_display = ['action', 'last_updated']
