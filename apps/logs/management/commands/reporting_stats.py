from collections import Counter
from typing import IO

from django.core.management.base import BaseCommand

from logs.models import (
    FlexibleReport,
)


class Command(BaseCommand):
    help = 'Go over all stored reports in reporting and print some stats'

    def add_arguments(self, parser):
        pass

    def histogram(self, counter: Counter, out: IO = None, top=20, base=None):
        out = out or self.stdout
        total = base if base else counter.total()
        largest = counter.most_common(1)[0][1]
        for k, v in counter.most_common(top):
            out.write(f'{"█" * int(60 * v / largest):60s} {k}: {v:4d} ({v / total:6.2%}) \n')
        out.write('\n')

    def handle(self, *args, **options):
        # report types
        rts = Counter()
        rt_counts = Counter()
        rows = Counter()
        columns = Counter()
        col_counts = Counter()
        row_col_combs = Counter()
        filters = Counter()
        fltr_counts = Counter()
        split_bys = Counter()
        trend_modes = Counter()
        tag_rollups = Counter()
        totals = Counter()

        fr_count = FlexibleReport.objects.count()
        for fr in FlexibleReport.objects.all():
            # report types
            reps = next(
                fltr['values']
                for fltr in fr.report_config['filters']
                if fltr['dimension'] == 'report_type'
            )
            for rt in reps:
                rts[rt] += 1
            rt_counts[len(reps)] += 1
            # rows
            row = fr.report_config.get('primary_dimension')
            rows[row] += 1
            # columns
            cols = fr.report_config['group_by']
            col_counts[len(cols)] += 1
            for col in cols:
                columns[col] += 1
                row_col_combs[(row, col)] += 1
            # filters
            fltr_count = 0
            for fltr in fr.report_config['filters']:
                if fltr['dimension'] != 'report_type':
                    filters[fltr['dimension']] += 1
                    fltr_count += 1
            fltr_counts[fltr_count] += 1
            # split_bys
            split_by = fr.report_config.get('split_by')
            split_bys[split_by[0] if split_by else None] += 1
            # trend modes
            trend_mode = fr.report_config.get('trend_mode', False)
            trend_modes[trend_mode] += 1
            # tag rollups
            tag_rollup = fr.report_config.get('tag_rollup', False)
            tag_rollups[tag_rollup] += 1
            # row_col_totals (row and col totals are allways the same)
            row_total = fr.report_config.get('row_totals', False)
            totals[row_total] += 1

        print('Report type stats:')
        self.histogram(rts, base=fr_count)

        print('Report type rt_counts in reports:')
        self.histogram(rt_counts, base=fr_count)

        print('Rows in reports:')
        self.histogram(rows, base=fr_count)

        print('Columns in reports:')
        self.histogram(columns, base=fr_count)

        print('Column counts in reports:')
        self.histogram(col_counts, base=fr_count)

        print('Row, column combinations in reports:')
        self.histogram(row_col_combs, base=fr_count)

        print('Filters in reports:')
        self.histogram(filters, base=fr_count)

        print('Filter counts in reports:')
        self.histogram(fltr_counts, base=fr_count)

        print('Split bys in reports:')
        self.histogram(split_bys, base=fr_count)

        print('Trend modes in reports:')
        self.histogram(trend_modes, base=fr_count)

        print('Tag rollups in reports:')
        self.histogram(tag_rollups, base=fr_count)

        print('Show totals in reports:')
        self.histogram(totals, base=fr_count)
