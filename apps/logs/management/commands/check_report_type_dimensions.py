import logging
from collections import Counter

from charts.models import ChartDefinition, ReportDataView, ReportViewToChartType
from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from logs.models import Dimension, ReportType, ReportTypeToDimension
from sushi.models import COUNTER_REPORTS, CounterReportType

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Checks that dimensions assigned to report types match what the readers have defined'

    dim_name_remap = {
        'Platform': {'en': 'Platform in COUNTER data', 'cs': 'Platforma v COUNTER datech'}
    }

    def add_arguments(self, parser):
        parser.add_argument('--fix-it', dest='fix_it', action='store_true')

    @atomic
    def handle(self, *args, **options):
        stats = Counter()
        fix_it = options['fix_it']
        seen_codes = set()
        for code, our_name, version, json, reader, sushi in COUNTER_REPORTS:
            # COUNTER_REPORTS contains more than one record for some reports,
            # we only want the first one
            if code in seen_codes:
                continue
            seen_codes.add(code)
            if not sushi:
                continue
            try:
                rt = ReportType.objects.get(short_name=code, source__isnull=True)
            except ReportType.DoesNotExist:
                print('Missing RT:', code)
                stats['missing_rt'] += 1
                rt = None
                if fix_it:
                    rt = ReportType.objects.create(short_name=code, name=our_name, source=None)
            else:
                if our_name and rt.name != our_name:
                    print(f'RT name mismatch ({code}): "{rt.name}" != "{our_name}"')
                    stats['rt_name_mismatch'] += 1
                    if fix_it:
                        rt.name = our_name
                        rt.save()
                        stats['fixed_rt_name'] += 1
            # check the report-data-view
            if rt and not rt.reportdataview_set.exists():
                # there are no data views, we will create a default one
                print('Missing data view for:', code)
                stats['missing_data_view'] += 1
                if fix_it:
                    rv = ReportDataView.objects.create(
                        base_report_type=rt,
                        name=rt.name,
                        short_name=rt.short_name,
                        is_standard_view=True,
                    )
                    # connect the generic charts to the new data view
                    for i, cd in enumerate(ChartDefinition.objects.filter(is_generic=True)):
                        ReportViewToChartType.objects.create(
                            chart_definition=cd, report_data_view=rv, position=10 * (i + 1)
                        )
                    stats['created_data_view'] += 1
            # check the dimensions
            if rt:
                reader_dims = set(reader.dimensions)
                rt_dims = set(rt.dimension_short_names)
                if rt_dims != reader_dims:
                    fixable = rt_dims.issubset(reader_dims)
                    print('Mismatch:', code, 'fixable' if fixable else 'CANNNOT FIX')
                    print('   ', rt.dimension_short_names)
                    print('   ', reader.dimensions)
                    stats[f'mismatch_{"fixable" if fixable else "unfixable"}'] += 1
                    if fixable and fix_it:
                        pos = len(rt.dimension_short_names)
                        for i, dim_name in enumerate(reader_dims - rt_dims):
                            if remap_data := self.dim_name_remap.get(dim_name):
                                def_names = {
                                    f'name_{lang}': value for lang, value in remap_data.items()
                                }
                            else:
                                def_names = {'name': dim_name}
                            dim, _ = Dimension.objects.get_or_create(
                                short_name=dim_name, source=None, defaults=def_names
                            )
                            ReportTypeToDimension.objects.create(
                                report_type=rt, dimension=dim, position=pos + i
                            )
                        assert {dim.short_name for dim in rt.dimensions.all()} == reader_dims
                        print('  Fixed!')
                else:
                    print('OK:', code)
                    stats['ok'] += 1
                # check COUNTER report type as well
                if not CounterReportType.objects.filter(report_type=rt).exists():
                    print('Missing CRT:', code)
                    stats['missing_crt'] += 1
                    if fix_it:
                        CounterReportType.objects.create(
                            code=code, name=our_name, report_type=rt, counter_version=version
                        )

        print('Stats:', stats)
