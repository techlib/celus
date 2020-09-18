from django.db import transaction
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path

from .models import PlatformImportAttempt
from core.models import DataSource


@admin.register(PlatformImportAttempt)
class PlatformImportAttemptAdmin(admin.ModelAdmin):
    change_list_template = "knowledgebase/platformimportattempt_changelist.html"
    list_display = (
        'created_timestamp',
        'source',
        'get_status',
        'created',
        'updated',
        'same',
        'total',
    )
    readonly_fields = (
        'source',
        'url',
        'kind',
        'created_timestamp',
        'started_timestamp',
        'downloaded_timestamp',
        'processing_timestamp',
        'end_timestamp',
        'data_hash',
        'stats',
        'error',
    )
    list_filter = ('source',)
    actions = ('plan',)

    def plan(self, request, queryset):
        for attempt in queryset:
            if attempt.status == PlatformImportAttempt.State.QUEUE:
                attempt.plan()

    plan.short_description = 'Run in background'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["knowledgebase_data_sources"] = DataSource.objects.filter(
            type=DataSource.TYPE_KNOWLEDGEBASE
        )
        return super().changelist_view(request, extra_context)

    def get_urls(self):
        urls = super().get_urls()
        extra_urls = [
            path('run-sync/', self.run_sync),
        ]
        return extra_urls + urls

    def run_sync(self, request):

        source = DataSource.objects.filter(type=DataSource.TYPE_KNOWLEDGEBASE).get(
            pk=request.POST["source"]
        )
        attempt = PlatformImportAttempt.objects.create(source=source)
        # plan it in celery
        # on_commit is required because there is some race condition
        # which causes DoesNotExist exception in celery task
        transaction.on_commit(lambda: attempt.plan())

        return HttpResponseRedirect("../")

    def get_status(self, obj: PlatformImportAttempt):
        return obj.status

    get_status.short_description = 'Status'

    def created(self, obj: PlatformImportAttempt):
        return (obj.stats and obj.stats.get("created", "0")) or ""

    def updated(self, obj: PlatformImportAttempt):
        return (obj.stats and obj.stats.get("updated", "0")) or ""

    def total(self, obj: PlatformImportAttempt):
        return (obj.stats and obj.stats.get("total", "0")) or ""

    def same(self, obj: PlatformImportAttempt):
        return (obj.stats and obj.stats.get("same", "0")) or ""
