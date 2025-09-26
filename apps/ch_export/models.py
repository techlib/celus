import secrets
import traceback
from typing import Optional, Tuple

from core.models import CreatedUpdatedMixin
from django.conf import settings
from django.core.cache import cache
from django.db import models, transaction
from django.db.models import Exists, OuterRef, Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from logs.logic.export_analytical import HCubeExport
from logs.logic.export_analytical.exports.hcube import sanitize_identifier
from logs.models import ImportBatch, ReportType

from ch_export.cubes import (
    ch_export_database_prefix,
    create_ch_export_backend,
    create_ch_export_database,
    create_ch_export_user,
)
from ch_export.helpers import SmarterStringIO


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
        celus_name = ch_export_database_prefix()
        if self.organization:
            return f"{celus_name}_{self.organization.pk}"
        else:
            return celus_name + "_all"

    def ch_backend(self):
        return create_ch_export_backend(self.ch_database)

    def create_batch(self):
        return AccessLogExportBatch.objects.create(export=self)

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

    def __str__(self):
        return f"Batch {self.created}"

    def get_status(self):
        tasks = self.accesslogexporttask_set
        if not tasks.exists():
            return "empty"

        if tasks.exclude(error="").exists():
            return "failed"
        elif tasks.filter(finished__isnull=True).exists():
            return "running"
        else:
            return "completed"


class AccessLogExportTask(models.Model):
    batch = models.ForeignKey(AccessLogExportBatch, on_delete=models.CASCADE)
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
        kwargs: dict = self.batch.export.settings.get("_default", {})
        kwargs.update(self.batch.export.settings.get(self.report_type.short_name, {}))
        stream = SmarterStringIO()
        try:
            exp = HCubeExport(
                table=sanitize_identifier(self.report_type.short_name),
                **kwargs,
                report_type=self.report_type,
                organization=self.batch.export.organization,
                cube_backend=self.batch.export.ch_backend(),
                stderr=stream,
            )
            exp.export(progress_monitor=self._progress)
            self.stats = exp.stats
        except Exception:
            self.error = traceback.format_exc() + "\n\n= Log follows:\n" + stream.getvalue()
            self.save()
            raise
        finally:
            self.finished = timezone.now()
            self.save()

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
