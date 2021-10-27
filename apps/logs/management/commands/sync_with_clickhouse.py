import logging
from time import time

from django.core.management.base import BaseCommand

from logs.logic.clickhouse import sync_accesslogs_with_clickhouse_superfast

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

    def handle(self, *args, **options):
        start = time()
        count = sync_accesslogs_with_clickhouse_superfast(ignore_timestamps=options['all'])
        logger.info('Duration: %s, Count: %s', time() - start, count)
