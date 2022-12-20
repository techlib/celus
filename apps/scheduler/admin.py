from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from logs.models import ImportBatch
from sushi.models import SushiFetchAttempt

from . import models


class FetchIntentionInline(admin.TabularInline):
    model = models.FetchIntention
    readonly_fields = ("intention_link", "url")
    fields = ("intention_link", "queue", "url", "when_processed", "start_date", "end_date")

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('queue')
        return qs.prefetch_related(
            'credentials', 'credentials__organization', 'credentials__platform'
        )

    def intention_link(self, obj: models.FetchIntention):
        url = reverse('admin:scheduler_fetchintention_change', args=[obj.pk])
        return format_html('<a href="{}">#{} - {}</a>', url, str(obj.pk), str(obj.credentials))

    def url(self, obj: models.FetchIntention):
        return obj.credentials.url

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


def wipe_harvest(modeladmin, request, queryset):
    queryset.wipe()


wipe_harvest.short_description = "Deletes harvest and also all related data"


@admin.register(models.Harvest)
class HarvestAdmin(admin.ModelAdmin):
    inlines = (FetchIntentionInline,)
    search_fields = ('last_updated_by__email', 'automatic__organization__name')
    readonly_fields = ('created',)

    list_display = (
        'pk',
        'automatic_month',
        'automatic_organization',
        'created',
        'last_updated',
        'last_updated_by',
        'stats_text',
        'attempts',
    )

    list_select_related = ['last_updated_by', 'automatic', 'automatic__organization']
    actions = [wipe_harvest]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate_stats()

    def stats_text(self, obj: models.Harvest):
        return f'{obj.finished}/{obj.total}'

    def attempts(self, obj: models.Harvest):
        return obj.attempt_count

    attempts.admin_order_field = 'attempt_count'

    stats_text.short_description = 'Processed'

    def automatic_month(self, obj: models.Harvest):
        if obj.automatic:
            return obj.automatic.month
        else:
            return ""

    automatic_month.short_description = "Month"

    def automatic_organization(self, obj: models.Harvest):
        if obj.automatic:
            return obj.automatic.organization.name
        else:
            return ""

    automatic_organization.short_description = "Organization"

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(models.Scheduler)
class SchedulerAdmin(admin.ModelAdmin):
    search_fields = ('url',)
    readonly_fields = ('current_intention',)

    list_display = (
        'url',
        'when_ready',
        'cooldown',
        'too_many_requests_delay',
        'service_not_available_delay',
        'service_busy_delay',
    )


class AttemptInline(admin.StackedInline):
    model = SushiFetchAttempt
    show_change_link = True


@admin.register(models.FetchIntention)
class FetchIntentionAdmin(admin.ModelAdmin):
    search_fields = (
        'harvest__pk',
        'harvest__last_updated_by__email',
        'credentials__organization__name',
        'credentials__platform__name',
    )

    list_filter = (
        'counter_report__code',
        'credentials__counter_version',
        'credentials__organization',
        'credentials__platform',
        'scheduler',
        ('when_processed', admin.EmptyFieldListFilter),
    )

    list_display = (
        'pk',
        'harvest_link',
        'queue_id',
        'not_before_repr',
        'when_processed_repr',
        'priority',
        'platform',
        'url',
        'code',
        'start_date',
        'end_date',
    )

    exclude = ('attempt',)
    readonly_fields = ('credentials', 'counter_report', 'attempt_link')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related(
            'credentials', 'credentials__platform', 'counter_report', 'attempt', 'harvest'
        )

    def attempt_link(self, obj: models.FetchIntention):
        if obj.attempt:
            url = reverse('admin:sushi_sushifetchattempt_change', args=[obj.attempt_id])
            return format_html('<a href="{}">{}</a>', url, str(obj.attempt))
        return ''

    def url(self, obj: models.FetchIntention):
        return obj.credentials.url

    def code(self, obj: models.FetchIntention):
        return obj.counter_report.code

    def platform(self, obj: models.FetchIntention):
        return obj.credentials.platform.name

    def not_before_repr(self, obj: models.FetchIntention):
        return obj.not_before.strftime("%Y-%m-%d %H:%M:%S")

    not_before_repr.admin_order_field = 'not_before'
    not_before_repr.short_description = "Not Before"

    def when_processed_repr(self, obj: models.FetchIntention):
        if obj.when_processed:
            return obj.not_before.strftime("%Y-%m-%d %H:%M:%S")
        else:
            return ""

    when_processed_repr.admin_order_field = 'when_processed'
    when_processed_repr.short_description = "When Processed"

    def harvest_link(self, obj: models.FetchIntention):

        return format_html(
            f'<a href="{ reverse("admin:scheduler_harvest_change", args=(obj.harvest.id,)) }">{ obj.harvest.id }</a>'
        )

    harvest_link.short_description = "Harvest"
    harvest_link.admin_order_field = 'harvest'
    harvest_link.allow_tags = True

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False
