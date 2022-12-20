import csv
import logging
from collections import Counter

from core.logic.dates import month_end, parse_date
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.transaction import atomic, on_commit
from logs.logic.clickhouse import delete_import_batch_from_clickhouse
from logs.models import ImportBatch
from scheduler.models import FetchIntention, Harvest
from sushi.models import CounterReportType, SushiCredentials

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = (
        'Helper script for reimport which takes a CSV of non-reimportable IBs produced by '
        '`reimport_data` and deals with the IBs. If it finds credentials for them, it will '
        'create a harvest for them, if it does not, it will remove the IBs.'
    )

    def add_arguments(self, parser):
        parser.add_argument('input_file', help='Input CSV file')
        parser.add_argument('--do-it', dest='do_it', action='store_true')

    @atomic
    def handle(self, *args, **options):
        stats = Counter()
        harvest_groups = {}
        ibs_to_delete = []
        with open(options['input_file'], 'r') as infile:
            reader = csv.DictReader(infile)
            for rec in reader:
                logger.debug('rec: %s', rec)
                try:
                    ib = ImportBatch.objects.get(pk=rec['pk'])
                except ImportBatch.DoesNotExist:
                    logger.warning('Missing IB: %d', rec['pk'])
                    stats['missing'] += 1
                else:
                    credentials = list(
                        SushiCredentials.objects.filter(
                            organization_id=rec['organization_id'],
                            platform_id=rec['platform_id'],
                            counter_reports__report_type_id=rec['report_type_id'],
                        )
                    )
                    if credentials:
                        # plan a harvest
                        harvest_key = (rec['organization_id'], rec['platform_id'])
                        if not (harvest_group := harvest_groups.get(harvest_key)):
                            harvest_group = []
                            harvest_groups[harvest_key] = harvest_group
                        counter_report = CounterReportType.objects.get(
                            report_type_id=rec['report_type_id']
                        )
                        start_date = parse_date(rec['date'])
                        end_date = month_end(start_date)
                        harvest_group.append(
                            FetchIntention(
                                credentials=credentials[0],
                                start_date=start_date,
                                end_date=end_date,
                                counter_report=counter_report,
                            )
                        )
                    # we delete the import batch but also all that are "blocked" by it
                    # - these should be also not reimportable but older
                    ibs_to_delete += ImportBatch.objects.filter(
                        organization_id=ib.organization_id,
                        platform_id=ib.platform_id,
                        report_type_id=ib.report_type_id,
                        date=ib.date,
                    ).values_list('pk', flat=True)

        logger.info(
            'Deleting import batches: %s', ImportBatch.objects.filter(pk__in=ibs_to_delete).delete()
        )
        fi_count = sum(len(val) for val in harvest_groups.values())
        logger.info('Creating %d fetch intentions', fi_count)
        for harvest_key, fi_group in harvest_groups.items():
            logger.debug(
                'Creating harvest for key "%s" with %d intentions', harvest_key, len(fi_group)
            )
            Harvest.plan_harvesting(fi_group, priority=FetchIntention.PRIORITY_NOW)

        def delete_from_clickhouse():
            if ibs_to_delete and settings.CLICKHOUSE_SYNC_ACTIVE:
                for ib_id in ibs_to_delete:
                    delete_import_batch_from_clickhouse(ib_id)

        on_commit(delete_from_clickhouse)

        if not options['do_it']:
            raise CommandError('Not doing anything - use --do-it to really make the changes')
