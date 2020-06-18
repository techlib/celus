import codecs
import csv
import logging
import os
from time import monotonic
from typing import IO
from zipfile import ZipFile, ZIP_DEFLATED

from django.conf import settings
from django.db.models import QuerySet
from django.core.cache import cache
from django.utils.timezone import now

from ..models import AccessLog, DimensionText, ReportType


logger = logging.getLogger(__name__)


class CSVExport(object):

    implicit_dims = {
        'platform': 'name',
        'metric': 'short_name',
        'organization': 'name',
        'target': 'name',
        'report_type': 'short_name',
        'date': None,
    }
    title_attrs = ['isbn', 'issn', 'eissn']
    outdir = 'export'

    def __init__(self, query_params: dict, zip_compress: bool = False, filename_base=None):
        self.query_params = query_params
        self.zip_compress = zip_compress
        if filename_base:
            self.filename_base = filename_base
        else:
            self.filename_base = self.create_filename_base()

    def create_filename_base(self) -> str:
        ts = now().strftime('%Y%m%d-%H%M%S.%f')
        filename = f'raw-data-{ts}'
        return filename

    @property
    def filename(self) -> str:
        if self.zip_compress:
            fname = self.filename_base + '.zip'
        else:
            fname = self.filename_base + '.csv'
        return os.path.join(self.outdir, fname)

    @property
    def file_url(self) -> str:
        return settings.MEDIA_URL + self.filename

    @property
    def file_path(self) -> str:
        return os.path.join(settings.MEDIA_ROOT, self.filename)

    @classmethod
    def create_outdir(cls):
        outdir = os.path.join(settings.MEDIA_ROOT, cls.outdir)
        if not os.path.exists(outdir):
            os.mkdir(outdir)

    def create_queryset(self):
        return AccessLog.objects.filter(**self.query_params)

    @property
    def record_count(self):
        return self.create_queryset().count()

    def export_raw_accesslogs_to_file(self):
        self.create_outdir()
        queryset = self.create_queryset()
        if self.zip_compress:
            with ZipFile(self.file_path, 'w', compression=ZIP_DEFLATED) as outzip:
                with outzip.open(self.filename_base + '.csv', 'w', force_zip64=True) as outfile:
                    writer = codecs.getwriter('utf-8')
                    encoder = writer(outfile)
                    self.export_raw_accesslogs_to_stream_lowlevel(encoder, queryset=queryset)
        else:
            with open(self.file_path, 'w') as outfile:
                self.export_raw_accesslogs_to_stream_lowlevel(outfile, queryset=queryset)

    def store_error(self):
        self.store_progress(-1)

    def store_progress(self, value):
        cache.set(self.filename_base, value)

    def export_raw_accesslogs_to_stream_lowlevel(self, stream: IO, queryset: QuerySet):
        start = monotonic()
        text_id_to_text = {
            dt['id']: dt['text'] for dt in DimensionText.objects.all().values('id', 'text')
        }
        logger.debug('Finished loading text remaps: %.2f s', monotonic() - start)
        rt_to_dimensions = {
            rt.pk: rt.dimensions_sorted
            for rt in ReportType.objects.filter(
                pk__in=queryset.distinct('report_type_id').values('report_type_id')
            )
        }
        logger.debug('Finished loading report_types and dimensions: %.2f s', monotonic() - start)
        # get all field names for the CSV
        field_name_map = {
            (f'{dim}__{attr}' if attr else dim): dim for dim, attr in self.implicit_dims.items()
        }
        field_name_map.update({f'target__{attr}': attr for attr in self.title_attrs})
        field_names = list(field_name_map.values())
        for tr, dims in rt_to_dimensions.items():
            field_names += [dim.short_name for dim in dims if dim.short_name not in field_names]
        field_names.append('value')
        logger.debug('Finished preparing field names: %.2f s', monotonic() - start)
        # values that will be retrieved from the accesslogs
        values = ['value', 'report_type_id']
        values += list(field_name_map.keys())
        values += [f'dim{i+1}' for i in range(7)]
        # crate the writer
        writer = csv.DictWriter(stream, field_names)
        writer.writeheader()
        # disable cachalot for this query
        logger.debug('Disabling cachalot for this query')
        queryset.query.cachalot_do_not_cache = True
        logger.debug('Finished preparing CSV writer: %.2f s', monotonic() - start)
        # write the records
        rec_num = 0
        for rec_num, log in enumerate(queryset.values(*values).iterator()):  # type: int, dict
            record = {attr_out: log.get(attr_in) for attr_in, attr_out in field_name_map.items()}
            record['value'] = log['value']
            record['date'] = log['date']
            for i, dim in enumerate(rt_to_dimensions[log['report_type_id']]):
                value = log.get(f'dim{i+1}')
                if dim.type == dim.TYPE_TEXT:
                    record[dim.short_name] = text_id_to_text.get(value, value)
                else:
                    record[dim.short_name] = value
            writer.writerow(record)
            if rec_num % 999 == 0:
                self.store_progress(rec_num + 1)
            if rec_num % 99999 == 0:
                logger.debug('Stored %d records: %.2f s', rec_num, monotonic() - start)
        self.store_progress(rec_num + 1)
