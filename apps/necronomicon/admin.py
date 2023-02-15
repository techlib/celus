import json

from django.contrib import admin, messages
from django.contrib.admin import TabularInline
from django.db.models import Count, Max
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext as _

from .models import Batch, Candidate


class CandidateInlineModelAdmin(TabularInline):
    model = Candidate
    extra = 0
    exclude = ["info"]
    readonly_fields = ["object", "stats"]

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def stats(self, obj):
        return format_html(
            "<div style='max-height: 10em;overflow-y:scroll'><pre>{}</pre></div>",
            json.dumps(obj.info.get("stats"), indent=2),
        )

    def object(self, obj):
        return format_html(
            "<div style='max-height: 10em;overflow-y:scroll'><pre>{}</pre></div>",
            json.dumps(obj.info.get("object"), indent=2),
        )


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    change_form_template = "necronomicon/admin/change_form.html"
    inlines = (CandidateInlineModelAdmin,)
    list_display = ('pk', 'created', 'object_type', 'candidates_count', 'status')
    actions = ['plan_delete']
    readonly_fields = ('created', 'task_result_url', 'status')

    def task_result_url(self, obj):
        url = reverse('admin:django_celery_results_taskresult_change', args=[obj.task_result_id])
        if obj.task_result:
            return format_html('<a href="{}">{}</a>', url, obj.task_result)
        else:
            return "-"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            candidates_count=Count('candidates'),
            # Batch should the same content type
            object_type=Max('candidates__content_type__model'),
        ).prefetch_related('candidates__content_type')

    def object_type(self, batch):
        return batch.object_type

    def candidates_count(self, batch):
        return batch.candidates_count

    def has_add_permission(self, request, obj=None):
        return False

    @admin.action(description=_("Plan to delete all related objects"))
    def plan_delete(self, request, queryset):
        passed = 0
        skipped = 0
        for batch in queryset:
            if batch.plan_delete_batch_targets():
                passed += 1
            else:
                skipped += 1

        messages.add_message(
            request,
            messages.SUCCESS,
            _('Planned to delete all related object for %(passed)s/%(total)s batches.')
            % dict(passed=passed, total=passed + skipped),
        )

    def response_change(self, request, obj):
        if "_delete_objects" in request.POST:
            self.plan_delete(request, Batch.objects.filter(pk=obj.pk))
            return HttpResponseRedirect(".")
        return super().response_change(request, obj)


class NecronomiconAdminMixin:
    def get_actions(self, request):
        self.actions = [e for e in self.actions] + ['delete_in_necronomicon']
        return super().get_actions(request)

    @admin.action(description=_("Plan to delete"))
    def delete_in_necronomicon(self, request, queryset):
        if batch := Batch.create_from_queryset(queryset):
            batch.plan_prepare_batch()

            url = reverse('admin:necronomicon_batch_change', args=[batch.id])
            text = _("Deletion is being prepared. You need to confirm it")
            messages.add_message(
                request, messages.SUCCESS, format_html(f"{text} <a href={url}>{_('here')}</a>.")
            )

    def has_delete_permission(self, request, obj=None):
        return False
