import csv
import logging
from collections import Counter
from time import monotonic

from django.core.management.base import BaseCommand
from django.db.models import Count, Min

from logs.logic.reimport import (
    find_import_batches_to_reimport,
    reimport_import_batch_with_fa,
    SourceFileMissingError,
    has_source_data_file,
    reimport_mdu_batch,
)
from logs.models import ImportBatch
from sushi.models import SushiCredentials

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = (
        'Goes over all import batches, removes the old data and reimports the data from source '
        'files.'
    )

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        self.trace_file = None
        self.trace_writer = None

    def add_arguments(self, parser):
        parser.add_argument('--do-it', dest='do_it', action='store_true')
        parser.add_argument('-p', dest='platform', help='short name of the platform to process')
        parser.add_argument(
            '-o', dest='organization', help='short name of the organization to process'
        )
        parser.add_argument('--id', dest='ib_id', help='Import batch ID')
        parser.add_argument(
            '-r', dest='report_type', help='short name of the report_type to process'
        )
        parser.add_argument(
            '-t',
            '--older-than',
            dest='older_than',
            help='Only reimport batches older than a set date (use ISO format)',
        )
        parser.add_argument(
            '--no-fa',
            dest='no_fa',
            action='store_true',
            help='Do not process import batches with FA',
        )
        parser.add_argument(
            '--no-mdu',
            dest='no_mdu',
            action='store_true',
            help='Do not process import batches with MDU',
        )
        parser.add_argument(
            '--trace-file',
            dest='trace_file',
            default=None,
            help='File into which to write duration information for each import batch',
        )

    def handle(self, *args, **options):
        filters = {}
        if options['platform']:
            filters['platform__short_name'] = options['platform']
        if options['report_type']:
            filters['report_type__short_name'] = options['report_type']
        if options['organization']:
            filters['organization__short_name'] = options['organization']
        if options['ib_id']:
            filters['pk'] = options['ib_id']
        qs = ImportBatch.objects.filter(**filters)
        reimport = find_import_batches_to_reimport(qs)
        logger.info(
            f'Reimport candidates: {reimport.reimportable.count()}\n'
            f'Delete candidates: {reimport.obsolete.count()}'
        )
        # some statistics on not importable stuff
        if reimport.no_source.exists():
            logger.warning(
                f'There are {reimport.no_source.count()} import batches to reimport without mdu '
                f'or fa! They are blocking another {reimport.blocked.count()} import batches'
            )
            stats = Counter()
            for ib in reimport.no_source:  # type: ImportBatch
                if SushiCredentials.objects.filter(
                    platform=ib.platform,
                    organization=ib.organization,
                    counter_reports__report_type=ib.report_type,
                ).exists():
                    stats['has_credentials'] += 1
                else:
                    stats['no_credentials'] += 1
            logger.info(f'Not reimportable stats: {stats}')

            for key in ('organization', 'platform'):
                logger.info(f'  {key.upper()}:')
                for rec in (
                    reimport.no_source.values(f'{key}__pk', f'{key}__short_name')
                    .annotate(count=Count('id'))
                    .order_by('-count')
                ):
                    logger.info(
                        f'    {rec[f"{key}__short_name"]} (#{rec[f"{key}__pk"]}): {rec["count"]}'
                    )
        to_do = reimport.reimportable
        if options['older_than']:
            to_do = to_do.filter(last_updated__lte=options['older_than'])
            logger.info(f"Older-than filter used - will process {to_do.count()} IB's")
            logger.info('Report types:')
            for _rec in to_do.values('report_type__short_name').annotate(count=Count('id')):
                logger.info(f"    {_rec['report_type__short_name']}: {_rec['count']}")

        if options['no_fa'] or options['no_mdu']:
            logger.warning(
                'NOTE: The above numbers do not reflect --no-fa and --no-mdu as these filters are '
                'applied later during the actual processing'
            )
        if not options['do_it']:
            # at least print some stats about missing files if not processing them
            missing_file = 0
            for ib in to_do:
                if not has_source_data_file(ib):
                    missing_file += 1
            if missing_file:
                logger.warning(
                    f'{missing_file} import batches have source but the file does not exist :('
                )
            logger.warning('Use --do-it to really do it.')
            return
        trace_writer = None
        if trace_file := options.get('trace_file'):
            self.trace_file = open(trace_file, 'w')
            self.trace_writer = csv.DictWriter(
                self.trace_file,
                ['ib', 'platform', 'organization', 'report_type', 'date', 'duration'],
            )
            self.trace_writer.writeheader()
        stats = Counter()
        start = monotonic()
        # `no_mdu` and `no_fa` are not applied to the queryset but rather applied on a case by case
        # basis during processing
        # the reason is that we need all the relevant import batches in the queryset to properly
        # detect overlaps, so we cannot apply these filters from the start
        # MDU first
        if not options['no_mdu']:
            for i, mdu_batch in enumerate(reimport.gen_mdu_batches()):
                # honor the 'older_than' filter even if it does not play very well with the filter
                # because many IBs may be in an MDU and all have to be processed at once
                if (
                    options['older_than']
                    and mdu_batch.mdu.import_batches.aggregate(oldest=Min('last_updated'))[
                        'oldest'
                    ].isoformat()
                    > options['older_than']
                ):
                    stats['mdu skip too new'] += 1
                    continue
                logger.info(f"Reimport MDU #{mdu_batch.mdu.pk}")
                try:
                    reimport_mdu_batch(mdu_batch)
                except SourceFileMissingError:
                    stats['mdu missing file'] += 1
                except Exception as exc:
                    logger.error('Error when reimporting: %s', exc)
                    stats['mdu reimport error'] += 1
                else:
                    stats['mdu reimport'] += 1
                if i and i % 10 == 0:
                    logger.info('Duration: %s, Stats: %s', monotonic() - start, stats)
            logger.info(
                'Finished processing MDUs. Duration: %s, Stats: %s', monotonic() - start, stats
            )
        else:
            logger.info('Skipping MDU processing')
        # then FA's
        if not options['no_fa']:
            stats['fa_total'] = to_do.count()
            for i, ib in enumerate(to_do):
                try:
                    logger.info(
                        f'Reimport IB #{ib.pk}, RT: {ib.report_type}, org: {ib.organization}, '
                        f'platform: {ib.platform}, date: {ib.date}'
                    )
                    t = monotonic()
                    ib_id = ib.pk  # pk will be emptied on delete, so we need to preserve it here
                    reimport_import_batch_with_fa(ib)
                    self.write_trace(ib_id, ib, monotonic() - t)
                except SourceFileMissingError:
                    stats['fa missing file'] += 1
                except Exception as exc:
                    logger.error('Error when reimporting: %s', exc)
                    stats['fa reimport error'] += 1
                else:
                    stats['fa reimport'] += 1
                if i and i % 10 == 0:
                    logger.info('===== Duration: %s, Stats: %s =====', monotonic() - start, stats)
            logger.info(
                'Finished processing FA. Duration: %s, Stats: %s', monotonic() - start, stats
            )
        else:
            logger.info('Skipping FA processing')

        if self.trace_file:
            self.trace_file.close()

    def write_trace(self, ib_id: int, ib: ImportBatch, duration: float):
        if self.trace_writer:
            self.trace_writer.writerow(
                {
                    'ib': ib_id,
                    'report_type': ib.report_type.short_name,
                    'organization': str(ib.organization),
                    'platform': str(ib.platform),
                    'date': str(ib.date),
                    'duration': duration,
                }
            )
            self.trace_file.flush()
