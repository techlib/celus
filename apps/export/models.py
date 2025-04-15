import secrets
import traceback
from typing import Optional, Tuple, Union

from core.tasks import async_mail_admins
from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.db.models import BooleanField, ExpressionWrapper, Q
from django.utils.timezone import now
from logs.logic.reporting.export import format_to_exporter
from logs.logic.reporting.filters import DateDimensionFilter
from logs.logic.reporting.helpers import user_visible_tags
from logs.logic.reporting.slicer import FlexibleDataSlicer, SlicerConfigError
from tags.models import Tag

from export.enums import FileFormat


class AnnotateObsoleteQueryset(models.QuerySet):
    def annotate_obsolete(self):
        return self.annotate(
            obsolete=ExpressionWrapper(
                Q(created__lt=now() - settings.EXPORT_DELETING_PERIOD), output_field=BooleanField()
            )
        )


class ExportBase(models.Model):
    NOT_STARTED = 0
    IN_PROGRESS = 1
    FINISHED = 2
    ERROR = 3

    STATUS_CHOICES = (
        (NOT_STARTED, "not started"),
        (IN_PROGRESS, "in progress"),
        (FINISHED, "finished"),
        (ERROR, "error"),
    )

    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES, default=NOT_STARTED)
    extra_info = models.JSONField(default=dict, help_text="Internal stuff", blank=True)
    output_file = models.FileField(upload_to="export", null=True, blank=True)

    class Meta:
        abstract = True

    @property
    def cache_key_base(self):
        return f"_export_{self.__class__.__name__}_{self.pk}"

    @property
    def cache_key_total(self):
        return self.cache_key_base + "_total"

    @property
    def cache_key_current(self):
        return self.cache_key_base + "_current"

    @property
    def owner_info(self) -> str:
        return ""

    def progress(self) -> Tuple[int, int]:
        if self.status == self.IN_PROGRESS:
            total = cache.get(self.cache_key_total, 0)
            current = cache.get(self.cache_key_current, 0)
            return current, total
        elif self.status == self.FINISHED:
            total = self.extra_info.get("record_count", 0)
            return total, total
        else:
            return 0, 0

    def file_size(self) -> int:
        size = self.extra_info.get("file_size")
        if size:
            return size
        if self.output_file:
            return self.output_file.size
        return 0

    def error_info(self) -> dict:
        error_detail = self.extra_info.get("error_detail")
        error_code = self.extra_info.get("error_code")
        return {"detail": error_detail, "code": error_code}

    def generate_filename(self):
        raise NotImplementedError

    def write_data(self, stream, progress_monitor=None) -> int:
        raise NotImplementedError

    def create_output_file(self, progress_monitor=None, raise_exception=False):
        self.status = self.IN_PROGRESS
        self.save()
        self.output_file.name = self.generate_filename()
        try:
            with self.output_file.open("wb") as outfile:
                rec_count = self.write_data(outfile, progress_monitor=progress_monitor)
        except SlicerConfigError as e:
            self.extra_info["error_detail"] = e.message
            self.extra_info["error_code"] = e.code
            self.status = self.ERROR
            if raise_exception:
                raise e
        except Exception as e:
            error_detail = str(e)
            error_tb = traceback.format_exc()[-1000:]  # last 1000 characters of traceback
            if len(error_detail) > 1000:
                error_detail = error_detail[:1000] + "..."
            self.extra_info["error_detail"] = error_detail
            self.extra_info["error_traceback"] = error_tb
            mail = (
                "Export id: {}\nOwner: {}\nException cls: {}\nException details: {}\n"
                "Traceback: {}\n"
            ).format(self.pk, self.owner_info, e.__class__.__name__, error_detail, error_tb)

            async_mail_admins.delay("Export error", mail)
            self.status = self.ERROR
            if raise_exception:
                raise e
        else:
            self.extra_info["record_count"] = rec_count
            self.extra_info["file_size"] = self.output_file.size
            self.status = self.FINISHED
        self.save()


class FlexibleDataExport(ExportBase):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    export_params = models.JSONField(
        default=dict, help_text="Serialized parameters of the export", blank=True
    )
    file_format = models.CharField(
        max_length=16, choices=FileFormat.choices, default=FileFormat.XLSX
    )
    name = models.CharField(max_length=120, default="", blank=True)

    objects = AnnotateObsoleteQueryset.as_manager()

    def __str__(self):
        return f"Export: {self.created}"

    @property
    def owner_info(self):
        return str(self.owner)

    @classmethod
    def create_from_slicer(
        cls,
        slicer: FlexibleDataSlicer,
        user,
        name: str = "",
        fmt: Optional[Union[str, FileFormat]] = None,
    ):
        return FlexibleDataExport.objects.create(
            owner=user,
            export_params=slicer.config(),
            file_format=cls.cleanup_format(fmt),
            name=name,
        )

    @classmethod
    def cleanup_format(cls, fmt: Optional[Union[str, FileFormat]]) -> FileFormat:
        if fmt in FileFormat.values:
            return FileFormat(fmt)
        if not fmt:
            return cls._meta.get_field("file_format").default
        if fmt.lstrip(".").lower() in ("zip", "csv"):
            return FileFormat.ZIP_CSV
        return FileFormat.XLSX

    def write_data(self, stream, progress_monitor=None) -> int:
        slicer = FlexibleDataSlicer.create_from_config(self.export_params)
        slicer.tag_filter = user_visible_tags(self.owner, selected_tag_class=slicer.tag_class)
        slicer.add_extra_organization_filter(self.owner.accessible_organizations())
        export_cls = format_to_exporter[self.file_format]
        exporter = export_cls(
            slicer,
            report_name=self.name,
            report_owner=self.owner,
            include_tags=True,
            include_row_totals=self.export_params["row_totals"],
            include_col_totals=self.export_params["col_totals"],
        )
        return exporter.stream_data_to_sink(stream, progress_monitor=progress_monitor)

    def generate_filename(self):
        ts = now().strftime("%Y%m%d-%H%M%S")
        ext = FileFormat.file_extension(self.file_format)
        return f"export-{self.pk}-{ts}.{ext}"


class FlexibleDataAPIExport(ExportBase):
    """
    Export of flexible data made through the API - it differs from `FlexibleDataExport` in that it
    does not have a user associated with it, but rather an organization.
    """

    owner_org = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE)
    report = models.ForeignKey("logs.FlexibleReport", on_delete=models.CASCADE)
    start_date = models.DateField(null=True, help_text="May override the report's start date")
    end_date = models.DateField(null=True, help_text="May override the report's end date")
    file_format = models.CharField(
        max_length=16, choices=FileFormat.choices, default=FileFormat.XLSX_NO_CHARTS
    )

    objects = AnnotateObsoleteQueryset.as_manager()

    def __str__(self):
        return f"API Export from #{self.report_id}: {self.created}"

    @property
    def owner_info(self):
        return str(self.owner_org)

    @classmethod
    def cleanup_format(cls, fmt: Optional[Union[str, FileFormat]]) -> FileFormat:
        if fmt in FileFormat.values:
            return FileFormat(fmt)
        if not fmt:
            return cls._meta.get_field("file_format").default
        if fmt.lstrip(".").lower() in ("zip", "csv"):
            return FileFormat.ZIP_CSV
        return FileFormat.XLSX_NO_CHARTS

    def finalize_slicer(self, slicer: FlexibleDataSlicer):
        """
        Finalize the slicer by adding organization filter, adjusting date filters, etc.
        """
        # override date filters if provided
        if self.start_date or self.end_date:
            new_filter = DateDimensionFilter("date", start=self.start_date, end=self.end_date)
            # we want to replace the current date filter with the one provided
            slicer.dimension_filters = [
                f for f in slicer.dimension_filters if not isinstance(f, DateDimensionFilter)
            ]
            slicer.dimension_filters.append(new_filter)
        # filter tags to only those accessible by the organization
        slicer.tag_filter = Q(pk__in=Tag.objects.org_accessible_tags(self.owner_org))
        # filter organizations to only the one that owns the report
        slicer.add_extra_organization_filter([self.owner_org_id])

    def write_data(self, stream, progress_monitor=None) -> int:
        params = self.report.deserialize_slicer_config()
        slicer = FlexibleDataSlicer.create_from_config(params)
        self.finalize_slicer(slicer)

        export_cls = format_to_exporter[self.file_format]
        exporter = export_cls(
            slicer,
            report_owner_org=self.owner_org,
            include_tags=True,
            include_row_totals=params.get("row_totals", False),
            include_col_totals=params.get("col_totals", False),
        )
        return exporter.stream_data_to_sink(stream, progress_monitor=progress_monitor)

    def generate_filename(self):
        ts = now().strftime("%Y%m%d-%H%M%S")
        ext = FileFormat.file_extension(self.file_format)
        # let's add some more randomness to the filename
        rand_token = secrets.token_hex(4)
        return f"api-export-{self.report_id}-{ts}-{rand_token}.{ext}"
