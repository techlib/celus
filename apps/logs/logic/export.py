import csv
import os
from typing import Iterable, IO

from django.conf import settings
from django.db.models import QuerySet
from django.utils.timezone import now

from ..models import AccessLog, DimensionText, ReportType


class CSVExporter(object):

    implicit_dims = {
        'platform': 'name',
        'metric': 'short_name',
        'organization': 'name',
        'target': 'name',
        'report_type': 'short_name',
        'date': None,
    }
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
        field_name_map = {(f'{dim}__{attr}' if attr else dim): dim
                          for dim, attr in self.implicit_dims.items()}
        field_name_map.update({f'target__{attr}': attr for attr in self.title_attrs})
        field_names = list(field_name_map.values())
        for tr, dims in rt_to_dimensions.items():
            field_names += [dim.short_name for dim in dims if dim.short_name not in field_names]
        field_names.append('value')
        # values that will be retrieved from the accesslogs
        values = ['value', 'report_type_id']
        values += list(field_name_map.keys())
        values += [f'dim{i+1}' for i in range(7)]
        # crate the writer
        writer = csv.DictWriter(stream, field_names)
        writer.writeheader()
        # write the records
        for al in queryset.values(*values).iterator():  # type: dict
            record = {attr_out: al.get(attr_in) for attr_in, attr_out in field_name_map.items()}
            record['value'] = al['value']
            record['date'] = al['date']
            for i, dim in enumerate(rt_to_dimensions[al['report_type_id']]):
                value = al.get(f'dim{i+1}')
                if dim.type == dim.TYPE_TEXT:
                    record[dim.short_name] = text_id_to_text.get(value, value)
                else:
                    record[dim.short_name] = value

            writer.writerow(record)

