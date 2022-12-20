import csv
import logging
from collections import Counter
from io import StringIO
from time import monotonic

from django.core.management.base import BaseCommand
from django.db.models import Count, Min, Q
from logs.logic.reimport import (
    SourceFileMissingError,
    find_import_batches_to_reimport,
    has_source_data_file,
    reimport_import_batch_with_fa,
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
        parser.add_argument(
            '--skip-stats',
            dest='skip_stats',
            action='store_true',
            help='Skip calculating some costly statistics for the output',
        )
        parser.add_argument(
            '--no-filecheck',
            dest='no_filecheck',
            action='store_true',
            help='Skip checking existence of source files',
        )
        parser.add_argument(
            '-m',
            '--show-missing-files',
            dest='show_missing_files',
            action='store_true',
            help='Show more info about missing input files',
        )

    def handle(self, *args, **options):
        filters = Q()
        for opt in ('platform', 'report_type', 'organization'):
            one_fltr = Q()
            if options[opt]:
                for val in options[opt].split(','):
                    val = val.strip()
                    if val.isdigit():
                        one_fltr |= Q(**{f'{opt}_id': int(val)})
                    else:
                        one_fltr |= Q(**{f'{opt}__short_name': val})
            filters &= one_fltr

        if options['ib_id']:
            filters &= Q(id=options['ib_id'])
        qs = ImportBatch.objects.filter(filters)

        reimport = find_import_batches_to_reimport(qs)
        logger.info(
            f'Reimport candidates: {reimport.reimportable.count()}\n'
            f'Delete candidates: {reimport.obsolete.count()}'
        )
        # some statistics on not importable stuff
        no_source = list(
            reimport.no_source.select_related('organization', 'platform', 'report_type')
        )
        if no_source:
            logger.warning(
                f'There are {len(no_source)} import batches to reimport without mdu '
                f'or fa! They are blocking another {reimport.blocked.count()} import batches'
            )
            stats = Counter()
            creds_cache = {}
            for ib in no_source:  # type: ImportBatch
                cache_key = (ib.platform_id, ib.organization_id, ib.report_type_id)
                exists = creds_cache.get(cache_key)
                if exists is None:
                    exists = SushiCredentials.objects.filter(
                        platform=ib.platform,
                        organization=ib.organization,
                        counter_reports__report_type=ib.report_type,
                    ).exists()
                    creds_cache[cache_key] = exists
                if exists:
                    stats['has_credentials'] += 1
                    ib.has_credentials_ = True
                else:
                    stats['no_credentials'] += 1
                    ib.has_credentials_ = False
            logger.info(f'Not reimportable stats: {stats}')

            if not options['skip_stats']:
                for key in ('organization', 'platform'):
                    detail_stats = Counter()
                    for ib in no_source:
                        detail_stats[getattr(ib, f'{key}_id')] += 1
                    key_remap = {
                        obj.pk: str(obj)
                        for obj in ImportBatch._meta.get_field(key).related_model.objects.filter(
                            pk__in=detail_stats.keys()
                        )
                    }
                    logger.info(f'  {key.capitalize()}:')
                    for obj_id, value in detail_stats.most_common():
                        logger.info(f'    {key_remap[obj_id]} (#{obj_id}): {value}')
                out = StringIO()
                keys = (
                    'pk',
                    'organization_id',
                    'organization',
                    'platform_id',
                    'platform',
                    'report_type_id',
                    'report_type',
                    'date',
                    'has_credentials_',
                )
                writer = csv.DictWriter(out, fieldnames=keys)
                writer.writeheader()
                for ib in sorted(
                    no_source, key=lambda x: tuple(str(getattr(x, _key)) for _key in keys)
                ):
                    writer.writerow({key: str(getattr(ib, key)) for key in keys})
                logger.info('  Individual import batches:')
                # we are writing this to stdout for easy redirection into a file
                self.stdout.write(out.getvalue())

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
            if not options['no_filecheck']:
                # at least print some stats about missing files if not processing them
                missing_file = 0
                for ib in to_do:
                    if not has_source_data_file(ib):
                        if options['show_missing_files']:
                            logger.debug(
                                f'Missing file: {ib.organization}, {ib.platform}, '
                                f'{ib.report_type}, {ib.date} (timestamp: {ib.created})'
                            )
                        missing_file += 1
                if missing_file:
                    logger.warning(
                        f'{missing_file} import batches have source but the file does not exist :('
                    )
            logger.warning('Use --do-it to really do it.')
            return
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
                except SourceFileMissingError as exc:
                    stats['mdu missing file'] += 1
                    logger.warning(
                        f'Missing source file: {exc.filename}, size: {exc.size}, '
                        f'checksum: {exc.checksum}'
                    )
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
        # exclude import batches processed as part of MDU - otherwise the newly created IBs
        # would be counted into `to_do` and tried to reimport
        to_do = to_do.exclude(mdu__isnull=False)
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
                    new_ib = reimport_import_batch_with_fa(ib)
                    logger.info(f"Created new IB: #{new_ib.pk}")
                    self.write_trace(ib_id, ib, monotonic() - t)
                except SourceFileMissingError as exc:
                    stats['fa missing file'] += 1
                    logger.warning(
                        f'Missing source file: {exc.filename}, size: {exc.size}, '
                        f'checksum: {exc.checksum}'
                    )
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
