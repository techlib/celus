import csv
import os
from typing import Iterable, IO

from django.conf import settings
from django.db.models import QuerySet
from django.utils.timezone import now

from ..models import AccessLog, DimensionText, ReportType


class CSVExporter(object):

    implicit_dims = ['platform', 'metric', 'organization', 'target', 'report_type']
    title_attrs = ['isbn', 'issn', 'eissn']

    def export_raw_accesslogs_to_file(self, query_params: dict) -> str:
        ts = now().strftime('%Y%m%d-%H%M%S.%f')
        file_path = f'export/raw-data-{ts}.csv'
        out_filename = os.path.join(settings.MEDIA_ROOT, file_path)
        queryset = AccessLog.objects.filter(**query_params)
        with open(out_filename, 'w') as outfile:
            self.export_raw_accesslogs_to_stream_lowlevel(outfile, queryset=queryset)
        return file_path

    def export_raw_accesslogs_to_stream_lowlevel(self, stream: IO, queryset: QuerySet):
        text_id_to_text = {dt['id']: dt['text']
                           for dt in DimensionText.objects.all().values('id', 'text')}
        rt_to_dimensions = {rt.pk: rt.dimensions_sorted for rt in
                            ReportType.objects.filter(pk__in=queryset.distinct('report_type_id').
                                                      values('report_type_id'))}
        # get all field names for the CSV
        field_names = self.implicit_dims + self.title_attrs
        for tr, dims in rt_to_dimensions.items():
            field_names += [dim.short_name for dim in dims]
        field_names.append('value')
        # crate the writer
        writer = csv.DictWriter(stream, field_names)
        writer.writeheader()
        # write the records
        for al in queryset.select_related(*self.implicit_dims).iterator():  # type: AccessLog
            record = {dim: str(getattr(al, dim)) for dim in self.implicit_dims}
            record['value'] = al.value
            for i, dim in enumerate(rt_to_dimensions[al.report_type_id]):
                value = getattr(al, f'dim{i+1}')
                if dim.type == dim.TYPE_TEXT:
                    record[dim.short_name] = text_id_to_text.get(value, value)
                else:
                    record[dim.short_name] = value
            if al.target:
                for attr in self.title_attrs:
                    record[attr] = getattr(al.target, attr)
            writer.writerow(record)

