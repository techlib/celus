import secrets
import traceback
from io import StringIO
from typing import TYPE_CHECKING, Optional, Tuple

from core.models import CreatedUpdatedMixin
from django.conf import settings
from django.core.cache import cache
from django.db import models, transaction
from django.db.models import Exists, OuterRef, Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from logs.models import ImportBatch, ReportType
from tags.models import AccessibleBy, OrganizationTag, PlatformTag, Tag, TitleTag

from ch_export.cubes import OrganizationTagCube, PlatformTagCube, TitleTagCube
from ch_export.helpers import SmarterStringIO

if TYPE_CHECKING:
    from logs.logic.export_analytical.exports.hcube import HCubeExport


class AccessLogExport(CreatedUpdatedMixin, models.Model):
    organization = models.OneToOneField(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="When empty, it represents export for the whole consortium",
    )
    settings = models.JSONField(default=dict, blank=True)
    enabled = models.BooleanField(default=True)
    ch_database = models.CharField(max_length=128, blank=True)
    ch_password = models.CharField(max_length=128, blank=True)

    class Meta:
        # only one export is allowed without an organization
        constraints = [
            models.UniqueConstraint(
                # we coalesce null to 0, so that we can use it in the unique constraint
                Coalesce("organization", models.Value(0)),
                name="only_one_consortium_export",
            )
        ]

    def __str__(self):
        note = f"organization = {self.organization}" if self.organization else "whole consortium"
        return f"AccessLogExport ({note})"

    def save(self, *args, **kwargs):
        from ch_export.cubes import (  # noqa - slow import
            create_ch_export_database,
            create_ch_export_user,
        )

        if not self.ch_database:
            self.ch_database = self.db_name()
            create_ch_export_database(self.ch_database)
        if not self.ch_password:
            self.ch_password = secrets.token_urlsafe(settings.CLICKHOUSE_EXPORT_PASSWORD_LENGTH)
            create_ch_export_user(self.ch_database, self.ch_database, self.ch_password)
        super().save(*args, **kwargs)

    def latest_batch(self):
        return self.accesslogexportbatch_set.order_by("-created").first()

    def db_name(self):
        from ch_export.cubes import ch_export_database_prefix  # noqa - slow import

        celus_name = ch_export_database_prefix()
        if self.organization:
            return f"{celus_name}_{self.organization.pk}"
        else:
            return celus_name + "_all"

    def ch_backend(self):
        from ch_export.cubes import create_ch_export_backend  # noqa - slow import

        return create_ch_export_backend(self.ch_database)

    def _ensure_ch_database_and_user_exists(self):
        from ch_export.cubes import create_ch_export_database, create_ch_export_user  # noqa - slow import

        create_ch_export_database(self.ch_database)
        create_ch_export_user(self.ch_database, self.ch_database, self.ch_password)

    def create_batch(self, start_tasks: bool = True):
        """
        if start_tasks is true, it will also create and start the tasks for the batch.
        """
        self._ensure_ch_database_and_user_exists()
        batch = AccessLogExportBatch.objects.create(export=self)
        if start_tasks:
            from ch_export.tasks import export_to_ch_task  # local import to avoid circular import

            for report_type in self.report_types():
                task = AccessLogExportTask.objects.create(batch=batch, report_type=report_type)
                celery_task = export_to_ch_task.apply_async((task.id,), countdown=2)
                task.task_id = celery_task.id
                task.save()
        return batch

    def report_types(self):
        """
        Return all report types which are not martedialized and have data.
        We find those by looking for import batches with non-zero record count
        and include interest report type as well.
        """
        # interest reporttype does not have import batches associated with it,
        # so we need to include it explicitly

        ib_qs = ImportBatch.objects.filter(record_count__gt=0)
        if self.organization:
            ib_qs = ib_qs.filter(organization=self.organization)

        condition = Exists(ib_qs.filter(report_type=OuterRef("pk")))
        if interest_rt := ReportType.objects.get_interest_rt_no_create():
            condition |= Q(pk=interest_rt.pk)
        return ReportType.objects.exclude_materialized().filter(condition)


class AccessLogExportBatch(models.Model):
    export = models.ForeignKey(AccessLogExport, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
        verbose_name_plural = "Access log export batches"

    def __str__(self):
        return f"Batch {self.created}"

    def get_status(self):
        if not self.tasks.exists():
            return "empty"

        if self.tasks.exclude(error="").exists():
            return "failed"
        elif self.tasks.filter(finished__isnull=True).exists():
            return "running"
        else:
            return "completed"

    def visibility_tag_qs(self):
        no_internal_tags = self.export.settings.get("_default", {}).get("no_internal_tags", False)
        filters = Q(can_see=AccessibleBy.EVERYBODY)
        if self.export.organization:
            filters |= Q(can_see=AccessibleBy.ORG_ADMINS, owner_org=self.export.organization)
        else:
            filters |= Q(can_see=AccessibleBy.ORG_ADMINS)
            filters |= Q(can_see=AccessibleBy.CONS_ADMINS)
        if no_internal_tags:
            filters &= Q(tag_class__internal=False)
        return Tag.objects.prefetch_related("tag_class").filter(filters)

    def refresh_export_tags(self, backend=None, organization=None):
        """
        Rebuild title/organization/platform tag helper tables for this batch's export.

        Args:
            backend: Optional backend to use (defaults to export.ch_backend())
            organization: Optional organization for visibility (defaults to export.organization)
        """
        if backend is None:
            backend = self.export.ch_backend()
        if organization is None:
            organization = self.export.organization

        # Build visibility queryset
        no_internal_tags = self.export.settings.get("_default", {}).get("no_internal_tags", False)
        filters = Q(can_see=AccessibleBy.EVERYBODY)
        if organization:
            filters |= Q(can_see=AccessibleBy.ORG_ADMINS, owner_org=organization)
        else:
            filters |= Q(can_see=AccessibleBy.ORG_ADMINS)
            filters |= Q(can_see=AccessibleBy.CONS_ADMINS)
        if no_internal_tags:
            filters &= Q(tag_class__internal=False)
        tag_qs = Tag.objects.prefetch_related("tag_class").filter(filters)

        # Title tags
        backend.initialize_storage(TitleTagCube)
        backend.sync_storage(TitleTagCube, drop=True)
        backend.delete_records(TitleTagCube.query())

        title_count = 0
        buf = []
        for title_id, tag_id, tag_name, tag_class_id, tag_class_name in (
            TitleTag.objects.filter(tag__in=tag_qs)
            .select_related("tag", "tag__tag_class")
            .values_list(
                "target_id", "tag_id", "tag__name", "tag__tag_class_id", "tag__tag_class__name"
            )
            .iterator()
        ):
            buf.append(
                dict(
                    title_id=title_id,
                    tag_id=tag_id,
                    tag__name=tag_name,
                    tag_class_id=tag_class_id,
                    tag_class__name=tag_class_name,
                )
            )
            title_count += 1

            if len(buf) >= 10000:
                backend.store_records(TitleTagCube, buf, dict_records=True, skip_cleanup=True)
                buf = []

        if buf:  # Flush the remainder
            backend.store_records(TitleTagCube, buf, dict_records=True, skip_cleanup=True)

        # Organization tags - only for consortium exports
        org_count = 0
        if organization is None:  # only for consortium exports
            backend.initialize_storage(OrganizationTagCube)
            backend.sync_storage(OrganizationTagCube, drop=True)
            backend.delete_records(OrganizationTagCube.query())

            buf = []
            for org_id, tag_id, tag_name, tag_class_id, tag_class_name in (
                OrganizationTag.objects.filter(tag__in=tag_qs)
                .select_related("tag", "tag__tag_class")
                .values_list(
                    "target_id", "tag_id", "tag__name", "tag__tag_class_id", "tag__tag_class__name"
                )
                .iterator()
            ):
                buf.append(
                    dict(
                        organization_id=org_id,
                        tag_id=tag_id,
                        tag__name=tag_name,
                        tag_class_id=tag_class_id,
                        tag_class__name=tag_class_name,
                    )
                )
                org_count += 1

                if len(buf) >= 10000:
                    backend.store_records(
                        OrganizationTagCube, buf, dict_records=True, skip_cleanup=True
                    )
                    buf = []

            if buf:  # Flush the remainder
                backend.store_records(
                    OrganizationTagCube, buf, dict_records=True, skip_cleanup=True
                )

        # Platform tags
        platform_count = 0
        backend.initialize_storage(PlatformTagCube)
        backend.sync_storage(PlatformTagCube, drop=True)
        backend.delete_records(PlatformTagCube.query())

        buf = []
        for platform_id, tag_id, tag_name, tag_class_id, tag_class_name in (
            PlatformTag.objects.filter(tag__in=tag_qs)
            .select_related("tag", "tag__tag_class")
            .values_list(
                "target_id", "tag_id", "tag__name", "tag__tag_class_id", "tag__tag_class__name"
            )
            .iterator()
        ):
            buf.append(
                dict(
                    platform_id=platform_id,
                    tag_id=tag_id,
                    tag__name=tag_name,
                    tag_class_id=tag_class_id,
                    tag_class__name=tag_class_name,
                )
            )
            platform_count += 1

            if len(buf) >= 10000:
                backend.store_records(PlatformTagCube, buf, dict_records=True, skip_cleanup=True)
                buf = []

        if buf:  # Flush the remainder
            backend.store_records(PlatformTagCube, buf, dict_records=True, skip_cleanup=True)

        return {"title_rows": title_count, "org_rows": org_count, "platform_rows": platform_count}


class AccessLogExportTask(models.Model):
    batch = models.ForeignKey(AccessLogExportBatch, on_delete=models.CASCADE, related_name="tasks")
    report_type = models.ForeignKey("logs.ReportType", on_delete=models.CASCADE)
    task_id = models.CharField(max_length=128, blank=True)

    created = models.DateTimeField(auto_now_add=True)
    started = models.DateTimeField(null=True, blank=True)
    finished = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)
    stats = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            # task_id is unique if it is not empty
            models.UniqueConstraint(
                fields=["task_id"], condition=~models.Q(task_id=""), name="unique_task_id"
            )
        ]

    def export_to_ch(self):
        with transaction.atomic():
            AccessLogExportTask.objects.filter(pk=self.pk).select_for_update().get()  # lock self
            self.refresh_from_db()
            if self.started is not None:
                return  # already started
            self.started = timezone.now()
            self.save()
        stream = SmarterStringIO()
        try:
            exp = self.create_exporter(stream)
            exp.export(progress_monitor=self._progress)
            self.stats = exp.stats
        except Exception:
            self.error = traceback.format_exc() + "\n\n= Log follows:\n" + stream.getvalue()
            self.save()
            raise
        finally:
            self.finished = timezone.now()
            self.save()
            # If all tasks in the batch finished, trigger tag refresh
            if not self.batch.tasks.filter(finished__isnull=True).exists():
                from celery import current_app

                current_app.send_task(
                    "ch_export.tasks.refresh_export_tags_task", args=(self.batch.pk,), countdown=2
                )

    def create_exporter(self, stderr_stream: Optional[StringIO] = None) -> "HCubeExport":
        from logs.logic.export_analytical import HCubeExport  # noqa - slow import
        from logs.logic.export_analytical.exports.hcube import sanitize_identifier  # noqa - slow import

        return HCubeExport(
            table=sanitize_identifier(self.report_type.short_name),
            **self.batch.export.settings.get("_default", {}),
            **self.batch.export.settings.get(self.report_type.short_name, {}),
            report_type=self.report_type,
            organization=self.batch.export.organization,
            cube_backend=self.batch.export.ch_backend(),
            stderr=stderr_stream,
        )

    @property
    def cache_key(self):
        return f"ch_export_task_{self.pk}"

    @property
    def progress_info(self) -> Tuple[Optional[int], Optional[int]]:
        return cache.get(self.cache_key + "_current"), cache.get(self.cache_key + "_total")

    @property
    def eta(self) -> Optional[str]:
        current, total = self.progress_info
        if not total or current is None:
            return None
        time_since_start = timezone.now() - self.started
        time_per_row = time_since_start / current
        remaining = (total - current) * time_per_row
        return remaining

    def _progress(self, progress: int, total: int):
        cache.set(self.cache_key + "_total", total)
        cache.set(self.cache_key + "_current", progress)
