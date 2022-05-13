import logging
import string
from collections import Counter
from time import monotonic

import xlsxwriter
from django.core.management.base import BaseCommand
from django.db import models
from django.db.models import Q, Sum, Count
from django.utils.translation import activate

from logs.models import ReportType, AccessLog, ManualDataUpload, ImportBatch
from sushi.models import SushiFetchAttempt, CounterReportType

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Compares the `default` database to the `old` one from the settings and creates a report'
    annot_keys = ['sum', 'ib_count', 'title_count']

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        self._cache = {}

    def add_arguments(self, parser):
        parser.add_argument(
            '-l', dest='lang', default='cs', help="language to use for object names"
        )
        parser.add_argument('outfile')

    def handle(self, *args, **options):
        self.ignored_rts = list(
            ReportType.objects.filter(
                Q(materialization_spec__isnull=False) | Q(short_name='interest')
            ).values_list('pk', flat=True)
        )
        base_qs = AccessLog.objects.exclude(report_type_id__in=self.ignored_rts)
        activate(options['lang'])

        workbook = xlsxwriter.Workbook(options['outfile'])
        self.base_fmt_dict = {'font_name': 'Arial', 'font_size': 9}  # , 'num_format': '#,##0'}
        self.base_fmt = workbook.add_format(self.base_fmt_dict)
        self.header_fmt = workbook.add_format({'bold': True, **self.base_fmt_dict})
        self.ok_fmt = workbook.add_format({'bg_color': '#ddffdd', **self.base_fmt_dict})
        self.warn_fmt = workbook.add_format({'bg_color': '#ffd0b0', **self.base_fmt_dict})
        self.perc_fmt = workbook.add_format({'num_format': '0.000%', **self.base_fmt_dict})
        self.ok_perc_fmt = workbook.add_format(
            {'num_format': '0.000%', 'bg_color': self.ok_fmt.bg_color, **self.base_fmt_dict}
        )
        self.warn_perc_fmt = workbook.add_format(
            {'num_format': '0.000%', 'bg_color': self.warn_fmt.bg_color, **self.base_fmt_dict}
        )

        # detail view - all months that have a change
        for spec in [
            {'name': 'organization', 'key': ('organization',), 'match': 'show'},
            {'name': 'platform', 'key': ('platform',), 'match': 'show'},
            {'name': 'report_type', 'key': ('report_type',), 'match': 'show'},
            {'name': 'date', 'key': ('date',), 'match': 'show'},
            # {'name': 'org-platform', 'key': ('organization', 'platform'), 'match': 'hide'},
            {
                'name': 'platform-org-report',
                'key': ('platform', 'organization', 'report_type'),
                'match': 'hide',
            },
            {
                'name': 'detail',
                'key': ('platform', 'organization', 'report_type', 'date'),
                'match': 'hide',
                'extra': ['title_count', 'filenames', 'ib_compare'],
            },
        ]:
            print("==", spec['name'], "==")
            sheet = workbook.add_worksheet(spec['name'])
            key = spec['key']
            mappings = {}
            is_fk = {}
            header_row = []
            for key_dim in key:
                mappings[key_dim] = {}
                field = AccessLog._meta.get_field(key_dim)
                if isinstance(field, models.ForeignKey):
                    mappings[key_dim] = {obj.pk: obj for obj in field.related_model.objects.all()}
                    is_fk[key_dim] = True
                    header_row.append(f'{key_dim} id')
                    header_row.append(key_dim)
                else:
                    is_fk[key_dim] = False
                    header_row.append(key_dim)

            header_row += ['before', 'after', 'diff', 'rel. diff']
            if 'title_count' in spec.get('extra', []):
                header_row += ['titles before', 'titles after', 'IBs before']
            # add notes column to make sure it is part of the auto-filter created later
            header_row += ['notes']
            sheet.write_row(0, 0, header_row, self.header_fmt)

            query_key = tuple(f'{key_dim}_id' if is_fk[key_dim] else key_dim for key_dim in key)
            qs = (
                base_qs.values(*query_key)
                .annotate(
                    sum=Sum('value'),
                    title_count=Count('target_id', distinct=True),
                    ib_count=Count('import_batch_id', distinct=True),
                )
                .order_by(*query_key)
            )
            old = {
                tuple(rec[k] for k in query_key): {
                    _k: _v for _k, _v in rec.items() if _k in self.annot_keys
                }
                for rec in qs.using('old')
            }

            row_idx = 0
            stats = Counter()
            max_lens = {key_dim: 0 for key_dim in key}
            seen_grp_ids = set()
            for i, rec in enumerate(qs):
                grp_id = tuple(rec[k] for k in query_key)
                seen_grp_ids.add(grp_id)
                old_rec = old.get(grp_id, {k: 0 for k in self.annot_keys})
                if self.process_row(
                    row_idx, is_fk, key, mappings, max_lens, old_rec, rec, sheet, spec, stats
                ):
                    row_idx += 1
            # process old stuff to see if something was missing in the new one
            for grp_id, old_value in old.items():
                if grp_id not in seen_grp_ids:
                    rec = {
                        (f'{key_dim}_id' if is_fk[key_dim] else key_dim): grp_id[i]
                        for i, key_dim in enumerate(key)
                    }
                    rec['sum'] = 0
                    if self.process_row(
                        row_idx, is_fk, key, mappings, max_lens, old_value, rec, sheet, spec, stats,
                    ):
                        row_idx += 1

            # adjust column widths
            col = 0
            for key_dim in key:
                if is_fk[key_dim]:
                    sheet.set_column(col, col, 4)
                    sheet.set_column(col + 1, col + 1, 6 + int(0.7 * max_lens[key_dim]))
                    col += 2
                else:
                    col += 1
            # the notes column width
            sheet.set_column(len(header_row) - 1, len(header_row) - 1, 48)
            # add auto-filter
            sheet.autofilter(0, 0, row_idx, len(header_row) - 1)
            # add conditional formatting
            rel_diff_idx = header_row.index('rel. diff')
            sheet.conditional_format(
                1,
                rel_diff_idx,
                row_idx,
                rel_diff_idx,
                {
                    'type': '3_color_scale',
                    'min_color': "#BB2222",
                    'mid_color': "#FFFFFF",
                    'max_color': "#22BB22",
                    'mid_type': 'num',
                    'mid_value': 0,
                },
            )

            print(" ", stats)
        workbook.close()

    def process_row(
        self, i, is_fk, key, mappings, max_lens, old_rec: dict, rec: dict, sheet, spec, stats
    ):
        new_value = rec['sum']
        old_value = old_rec['sum']
        if old_value == new_value:
            stats['match'] += 1
            if spec['match'] == 'hide':
                return False
            fmt = self.ok_fmt
            cur_perc_fmt = self.ok_perc_fmt
        else:
            fmt = self.warn_fmt if spec['match'] != 'hide' else self.base_fmt
            cur_perc_fmt = self.warn_perc_fmt if spec['match'] != 'hide' else self.perc_fmt
            stats['mismatch'] += 1
        row = []
        for key_dim in key:
            if is_fk[key_dim]:
                key_attr = f'{key_dim}_id'
                row.append(rec[key_attr])
                s = str(mappings[key_dim].get(rec[key_attr], rec[key_attr]))
                row.append(s)
                max_lens[key_dim] = max(max_lens[key_dim], len(s))
            else:
                row.append(str(rec[key_dim]))
        sheet.write_row(i + 1, 0, [*row, old_value, new_value], fmt)
        # writing formulas with empty value to force recalc in LibreOffice
        letter1 = string.ascii_letters[len(row) + 1]
        letter2 = string.ascii_letters[len(row)]
        letter3 = string.ascii_letters[len(row) + 2]
        sheet.write_formula(i + 1, len(row) + 2, f'={letter1}{i + 2}-{letter2}{i + 2}', fmt, '')
        sheet.write_formula(
            i + 1, len(row) + 3, f'={letter3}{i + 2}/{letter2}{i + 2}', cur_perc_fmt, ''
        )
        last_col = len(row) + 3
        fltr = {k: v for k, v in rec.items() if k not in self.annot_keys}
        # write extra info
        if 'title_count' in spec.get('extra', []):
            sheet.write_row(
                i + 1,
                last_col + 1,
                [
                    old_rec.get('title_count', 0),
                    rec.get('title_count', 0),
                    old_rec.get('ib_count', 0),
                ],
                self.base_fmt,
            )
            last_col += 3
        if 'filenames' in spec.get('extra', []):
            ib_subq = ImportBatch.objects.filter(**fltr).values('id').distinct()
            fas = SushiFetchAttempt.objects.filter(import_batch_id__in=ib_subq.using('old')).using(
                'old'
            )
            mdus = ManualDataUpload.objects.filter(import_batches__in=ib_subq.using('old')).using(
                'old'
            )
            fnames = [fa.data_file.name for fa in [*fas, *mdus]]

            if len(fnames) == 0:
                # no files, try with current DB
                fas = SushiFetchAttempt.objects.filter(import_batch_id__in=ib_subq)
                mdus = ManualDataUpload.objects.filter(import_batches__in=ib_subq)
                fnames = [fa.data_file.name for fa in [*fas, *mdus]]

            # sheet.write_comment(
            #     i + 1, last_col, "Filenames:\n\n" + '\n'.join(fnames), {'x_scale': 3.0}
            # )
            fnames.sort()
            sheet.write_string(i + 1, last_col + 1, '; '.join(fnames), self.base_fmt)
            last_col += 1
            file_comp = []
            if len(fnames) == 2:
                try:
                    dims1 = self.counter_file_stats(fnames[0], fltr['report_type_id'])
                except Exception as exc:
                    logger.error(f'Error reading {fnames[0]}: {exc}')
                    dims1 = {}
                try:
                    dims2 = self.counter_file_stats(fnames[1], fltr['report_type_id'])
                except Exception as exc:
                    logger.error(f'Error reading {fnames[1]}: {exc}')
                    dims2 = {}
                seen_keys = set()
                for key, values1 in dims1.items():
                    values2 = dims2.get(key, set())
                    if values1 ^ values2:
                        file_comp.append(
                            f'{key}: {len(values1 - values2)} < {len(values1 & values2)} > '
                            f'{len(values2 - values1)}'
                        )
                    seen_keys.add(key)
                for key, values2 in dims2.items():
                    if key not in seen_keys:
                        file_comp.append(f'{key}: 0 < 0 > {len(values2)}')
            if file_comp:
                sheet.write_string(i + 1, last_col + 1, '; '.join(file_comp), self.base_fmt)
                logger.debug(file_comp)
        return True

    def counter_file_stats(self, filename: str, report_type_id: int):
        logger.debug(f'reading {filename}')
        crt = CounterReportType.objects.get(report_type_id=report_type_id)

        is_json = True
        try:
            with open('media/' + filename, 'rb') as infile:
                char = infile.read(1)
                while char and char.isspace():
                    char = infile.read(1)
                if char not in b'[{':
                    is_json = False
        except FileNotFoundError:
            return {}

        reader = crt.get_reader_class(json_format=is_json)()
        unique_values = {}
        for rec in reader.file_to_records('media/' + filename):
            for key, value in rec.dimension_data.items():
                if key not in unique_values:
                    unique_values[key] = {value}
                else:
                    unique_values[key].add(value)
        return unique_values
