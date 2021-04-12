from typing import Tuple

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.utils.timezone import now

from logs.logic.queries import FlexibleDataSlicer, FlexibleDataExporter


class ExportBase(models.Model):

    NOT_STARTED = 0
    IN_PROGRESS = 1
    FINISHED = 2

    STATUS_CHOICES = (
        (NOT_STARTED, 'not started'),
        (IN_PROGRESS, 'in progress'),
        (FINISHED, 'finished'),
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


class FlexibleDataExport(ExportBase):

    export_params = models.JSONField(
        default=dict, help_text='Serialized parameters of the export', blank=True
    )

    def __str__(self):
        return f'Export: {self.created}'

    @classmethod
    def create_from_slicer(cls, slicer: FlexibleDataSlicer, user):
        this = FlexibleDataExport(owner=user, export_params=slicer.config(),)
        this.save()
        return this

    def write_data(self, stream, progress_monitor=None) -> int:
        slicer = FlexibleDataSlicer.create_from_config(self.export_params)
        slicer.add_extra_organization_filter(self.owner.accessible_organizations())
        exporter = FlexibleDataExporter(slicer)
        return exporter.stream_data_to_sink(stream, progress_monitor=progress_monitor)

    def create_output_file(self, progress_monitor=None):
        self.status = self.IN_PROGRESS
        self.save()
        self.output_file.name = self.generate_filename()
        with self.output_file.open('w') as outfile:
            rec_count = self.write_data(outfile, progress_monitor=progress_monitor)
        self.extra_info['record_count'] = rec_count
        self.extra_info['file_size'] = self.output_file.size
        self.status = self.FINISHED
        self.save()

    def generate_filename(self):
        ts = now().strftime('%Y%m%d-%H%M%S')
        return f'export-{self.pk}-{ts}.csv'
