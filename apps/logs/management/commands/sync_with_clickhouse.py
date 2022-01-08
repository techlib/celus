import logging
from time import time

from django.core.management.base import BaseCommand
from django.db.models import Q, F

from logs.logic.clickhouse import (
    sync_accesslogs_with_clickhouse_superfast,
    sync_import_batch_with_clickhouse,
)
from logs.models import ImportBatch, ImportBatchSyncLog

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Sync with ClickHouse'

    def add_arguments(self, parser):
        parser.add_argument(
            '-a',
            dest='all',
            action='store_true',
            help='ignore timestamps and process all import batches',
        )
        parser.add_argument(
            '-m',
            dest='save_memory',
            action='store_true',
            help='use a much slower but memory friendly (for the postgres server) method',
        )

    def handle(self, *args, **options):
        start = time()
        if options['save_memory']:
            count = 0
            qs = ImportBatch.objects.all()
            if not options['all']:
                qs = qs.filter(
                    Q(last_clickhoused__isnull=True) | Q(last_clickhoused__lt=F('last_updated'))
                )
            logger.info('Found %d unprocessed import batches', qs.count())
            for ib in qs.iterator():  # type: ImportBatch
                sync_import_batch_with_clickhouse(ib)
                count += 1
                if count and count % 100 == 0:
                    logger.info('Processed import batches: %d', count)
        else:
            count = sync_accesslogs_with_clickhouse_superfast(ignore_timestamps=options['all'])
        logger.info('Duration: %s, Count: %s', time() - start, count)
