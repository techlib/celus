import logging
import string
from collections import Counter

import xlsxwriter
from django.core.management.base import BaseCommand
from django.db import models
from django.db.models import Q, Sum, Count
from django.utils.translation import activate

from logs.models import ReportType, AccessLog, ManualDataUpload
from sushi.models import SushiFetchAttempt

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Compares the `default` database to the `old` one from the settings and creates a report'

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
                'extra': ['title_count', 'filenames'],
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
            qs = base_qs.values(*query_key).annotate(sum=Sum('value')).order_by(*query_key)
            old = {tuple(rec[k] for k in query_key): rec['sum'] for rec in qs.using('old')}

            row_idx = 0
            stats = Counter()
            max_lens = {key_dim: 0 for key_dim in key}
            seen_grp_ids = set()
            for rec in qs:
                grp_id = tuple(rec[k] for k in query_key)
                seen_grp_ids.add(grp_id)
                old_value = old.get(grp_id, 0)
                if self.process_row(
                    row_idx, is_fk, key, mappings, max_lens, old_value, rec, sheet, spec, stats
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

    def process_row(self, i, is_fk, key, mappings, max_lens, old_value, rec, sheet, spec, stats):
        new_value = rec['sum']
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
        sheet.write_row(
            i + 1, 0, [*row, old_value, new_value], fmt,
        )
        # writing formulas with empty value to force recalc in LibreOffice
        letter1 = string.ascii_letters[len(row) + 1]
        letter2 = string.ascii_letters[len(row)]
        letter3 = string.ascii_letters[len(row) + 2]
        sheet.write_formula(i + 1, len(row) + 2, f'={letter1}{i + 2}-{letter2}{i + 2}', fmt, '')
        sheet.write_formula(
            i + 1, len(row) + 3, f'={letter3}{i + 2}/{letter2}{i + 2}', cur_perc_fmt, ''
        )
        last_col = len(row) + 3
        fltr = dict(rec)
        del fltr['sum']
        # write extra info
        if 'title_count' in spec.get('extra', []):
            detail_new = (
                AccessLog.objects.exclude(report_type_id__in=self.ignored_rts)
                .filter(**fltr)
                .aggregate(
                    title_count=Count(
                        'target_id', distinct=True, filter=Q(target_id__isnull=False)
                    ),
                    ib_count=Count('import_batch_id', distinct=True),
                )
            )
            detail_old = (
                AccessLog.objects.exclude(report_type_id__in=self.ignored_rts)
                .filter(**fltr)
                .using('old')
                .aggregate(
                    title_count=Count(
                        'target_id', distinct=True, filter=Q(target_id__isnull=False)
                    ),
                    ib_count=Count('import_batch_id', distinct=True),
                )
            )
            sheet.write_row(
                i + 1,
                last_col + 1,
                [detail_old['title_count'], detail_new['title_count'], detail_old['ib_count']],
                self.base_fmt,
            )
            last_col += 3
        if 'filenames' in spec.get('extra', []):
            al_subq = (
                AccessLog.objects.exclude(report_type_id__in=self.ignored_rts)
                .filter(**fltr)
                .values('import_batch_id')
                .distinct()
            )
            fas = SushiFetchAttempt.objects.filter(import_batch_id__in=al_subq.using('old')).using(
                'old'
            )
            mdus = ManualDataUpload.objects.filter(import_batches__in=al_subq.using('old')).using(
                'old'
            )
            fnames = [fa.data_file.name for fa in [*fas, *mdus]]

            if len(fnames) == 0:
                # no files, try with current DB
                fas = SushiFetchAttempt.objects.filter(import_batch_id__in=al_subq)
                mdus = ManualDataUpload.objects.filter(import_batches__in=al_subq)
                fnames = [fa.data_file.name for fa in [*fas, *mdus]]

            sheet.write_comment(
                i + 1, last_col, "Filenames:\n\n" + '\n'.join(fnames), {'x_scale': 3.0}
            )
        sheet.write_string(i + 1, last_col + 1, '', self.base_fmt)
        last_col += 1
        return True
