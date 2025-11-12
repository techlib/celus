from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin

from ch_export.models import AccessLogExport, AccessLogExportBatch, AccessLogExportTask


@admin.register(AccessLogExport)
class AccessLogExportAdmin(ModelAdmin):
    list_display = ["organization", "enabled", "latest_batch", "status"]
    readonly_fields = ["ch_password"]
    actions = ["start_export"]

    def status(self, obj):
        batch = obj.latest_batch()
        return batch.get_status() if batch else None

    def start_export(self, request, queryset):
        """
        Start export by creating a new batch for selected exports.
        """
        if not queryset.exists():
            self.message_user(request, "No exports selected.", level=messages.WARNING)
            return

        started_count = 0
        for export in queryset:
            if not export.enabled:
                self.message_user(
                    request,
                    f"Export for {export.organization or 'consortium'} is disabled. Skipping.",
                    level=messages.WARNING,
                )
                continue
            try:
                batch = export.create_batch(start_tasks=True)
                started_count += 1
                self.message_user(
                    request,
                    f"Started export batch for {export.organization or 'consortium'} "
                    f"(Batch ID: {batch.id})",
                    level=messages.SUCCESS,
                )
            except Exception as e:
                self.message_user(
                    request,
                    f"Failed to start export for {export.organization or 'consortium'}: {str(e)}",
                    level=messages.ERROR,
                )

        if started_count > 0:
            self.message_user(
                request,
                f"Successfully started {started_count} export batch(es).",
                level=messages.SUCCESS,
            )

    start_export.short_description = "Start export"


class ExportTaskFilter(admin.SimpleListFilter):
    title = "success"
    parameter_name = "success"

    def lookups(self, request, model_admin):
        return (("yes", "Yes"), ("no", "No"), ("unfinished", "Unfinished"))

    def queryset(self, request, queryset):
        if self.value() == "unfinished":
            return queryset.filter(finished__isnull=True)
        if self.value() == "yes":
            return queryset.filter(error="")
        if self.value() == "no":
            return queryset.exclude(error="")
        return queryset


@admin.register(AccessLogExportTask)
class AccessLogExportTaskAdmin(ModelAdmin):
    list_display = [
        "export",
        "batch_id",
        "report_type",
        "created",
        "started",
        "duration",
        "processed_ibs",
        "progress",
        "eta",
        "success",
    ]
    list_filter = ["batch__export", ExportTaskFilter, "report_type"]
    list_select_related = ["batch", "batch__export", "batch__export__organization", "report_type"]
    ordering = ["-created"]
    readonly_fields = [
        "batch",
        "report_type",
        "task_id",
        "created",
        "started",
        "finished",
        "error",
        "stats",
    ]

    def export(self, obj):
        return obj.batch.export

    def duration(self, obj):
        if obj.finished:
            return round((obj.finished - obj.started).total_seconds(), 2)
        return "-"

    def eta(self, obj):
        if obj.eta is None:
            return "-"
        return str(obj.eta).split(".")[0]

    def progress(self, obj):
        current, total = obj.progress_info
        if not total or current is None:
            return "-"
        return f"{current} / {total} ({current / total * 100:.2f}%)"

    def processed_ibs(self, obj):
        return obj.stats.get("new_ibs_count", 0)

    def success(self, obj):
        if obj.error:
            return False
        if obj.finished:
            return True
        return None

    success.boolean = True

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(AccessLogExportBatch)
class AccessLogExportBatchAdmin(ModelAdmin):
    list_display = ["id", "export", "created", "status"]
    list_filter = ["export", "created"]
    list_select_related = ["export", "export__organization"]
    ordering = ["-created"]
    readonly_fields = ["export", "created"]

    def status(self, obj):
        return obj.get_status()
