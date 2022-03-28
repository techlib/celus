import logging
from collections import Counter

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from logs.models import ReportType, ReportTypeToDimension, Dimension
from sushi.models import COUNTER_REPORTS

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
        for code, version, json, reader, sushi in COUNTER_REPORTS:
            if not sushi:
                continue
            try:
                rt = ReportType.objects.get(short_name=code, source__isnull=True)
            except ReportType.DoesNotExist:
                print('Missing RT:', code)
                stats['missing_rt'] += 1
                rt = None
                if fix_it:
                    rt = ReportType.objects.create(short_name=code, name=code, source=None)
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
                            def_names = {}
                            if dim_name in self.dim_name_remap:
                                def_names = {
                                    f'name_{lang}': value
                                    for lang, value in self.dim_name_remap[dim_name].items()
                                }
                            dim, _ = Dimension.objects.get_or_create(
                                short_name=dim_name,
                                source=None,
                                defaults={
                                    'name': self.dim_name_remap.get(dim_name, dim_name),
                                    'type': 2,
                                    **def_names,
                                },
                            )
                            ReportTypeToDimension.objects.create(
                                report_type=rt, dimension=dim, position=pos + i
                            )
                        assert {dim.short_name for dim in rt.dimensions.all()} == reader_dims
                        print('  Fixed!')
                else:
                    print('OK:', code)
                    stats['ok'] += 1
        print('Stats:', stats)
