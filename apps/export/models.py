from typing import Optional, Tuple, Union

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.db.models import BooleanField, ExpressionWrapper, Q
from django.utils.timezone import now
from export.enums import FileFormat
from logs.logic.reporting.export import FlexibleDataExcelExporter, FlexibleDataZipCSVExporter
from logs.logic.reporting.slicer import FlexibleDataSlicer, SlicerConfigError


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
        (NOT_STARTED, 'not started'),
        (IN_PROGRESS, 'in progress'),
        (FINISHED, 'finished'),
        (ERROR, 'error'),
    )

    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES, default=NOT_STARTED)
    extra_info = models.JSONField(default=dict, help_text='Internal stuff', blank=True)
    output_file = models.FileField(upload_to='export', null=True, blank=True)

    class Meta:
        abstract = True

    @property
    def cache_key_base(self):
        return f'_export_{self.__class__.__name__}_{self.pk}'

    @property
    def cache_key_total(self):
        return self.cache_key_base + '_total'

    @property
    def cache_key_current(self):
        return self.cache_key_base + '_current'

    def progress(self) -> Tuple[int, int]:
        if self.status == self.IN_PROGRESS:
            total = cache.get(self.cache_key_total, 0)
            current = cache.get(self.cache_key_current, 0)
            return current, total
        elif self.status == self.FINISHED:
            total = self.extra_info.get('record_count', 0)
            return total, total
        else:
            return 0, 0

    def file_size(self) -> int:
        size = self.extra_info.get('file_size')
        if size:
            return size
        if self.output_file:
            return self.output_file.size
        return 0

    def error_info(self) -> dict:
        error_detail = self.extra_info.get('error_detail')
        error_code = self.extra_info.get('error_code')
        return {'detail': error_detail, 'code': error_code}


class FlexibleDataExport(ExportBase):

    objects = AnnotateObsoleteQueryset.as_manager()
    format_to_exporter = {
        FileFormat.XLSX: FlexibleDataExcelExporter,
        FileFormat.ZIP_CSV: FlexibleDataZipCSVExporter,
    }

    export_params = models.JSONField(
        default=dict, help_text='Serialized parameters of the export', blank=True
    )
    file_format = models.CharField(
        max_length=10, choices=FileFormat.choices, default=FileFormat.XLSX
    )
    name = models.CharField(max_length=120, default='', blank=True)

    def __str__(self):
        return f'Export: {self.created}'

    @classmethod
    def create_from_slicer(
        cls,
        slicer: FlexibleDataSlicer,
        user,
        name: str = '',
        fmt: Optional[Union[str, FileFormat]] = None,
    ):
        this = FlexibleDataExport(
            owner=user,
            export_params=slicer.config(),
            file_format=cls.cleanup_format(fmt),
            name=name,
        )
        this.save()
        return this

    @classmethod
    def cleanup_format(cls, fmt: Optional[Union[str, FileFormat]]) -> FileFormat:
        if fmt in FileFormat.values:
            return FileFormat[fmt]
        if not fmt:
            return cls._meta.get_field('file_format').default
        if fmt.lstrip('.').lower() in ('zip', 'csv'):
            return FileFormat.ZIP_CSV
        return FileFormat.XLSX

    def write_data(self, stream, progress_monitor=None) -> int:
        slicer = FlexibleDataSlicer.create_from_config(self.export_params)
        slicer.add_extra_organization_filter(self.owner.accessible_organizations())
        export_cls = self.format_to_exporter[self.file_format]
        exporter = export_cls(
            slicer, report_name=self.name, report_owner=self.owner, include_tags=True
        )
        return exporter.stream_data_to_sink(stream, progress_monitor=progress_monitor)

    def create_output_file(self, progress_monitor=None, raise_exception=False):
        self.status = self.IN_PROGRESS
        self.save()
        self.output_file.name = self.generate_filename()
        try:
            with self.output_file.open('wb') as outfile:
                rec_count = self.write_data(outfile, progress_monitor=progress_monitor)
        except SlicerConfigError as e:
            self.extra_info['error_detail'] = e.message
            self.extra_info['error_code'] = e.code
            self.status = self.ERROR
            if raise_exception:
                raise e
        except Exception as e:
            self.extra_info['error_detail'] = str(e)
            self.status = self.ERROR
            if raise_exception:
                raise e
        else:
            self.extra_info['record_count'] = rec_count
            self.extra_info['file_size'] = self.output_file.size
            self.status = self.FINISHED
        self.save()

    def generate_filename(self):
        ts = now().strftime('%Y%m%d-%H%M%S')
        ext = FileFormat.file_extension(self.file_format)
        return f'export-{self.pk}-{ts}.{ext}'
