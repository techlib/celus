import logging
from time import time

from django.core.management.base import BaseCommand
from django.db import connection

from logs.logic.materialized_interest import recompute_interest_by_batch
from logs.models import ImportBatch

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Sync interest data'

    def add_arguments(self, parser):
        parser.add_argument('-p', dest='platform', help='short name of the platform to process')

    def handle(self, *args, **options):
        if options['platform']:
            qs = ImportBatch.objects.filter(platform__short_name=options['platform'])
        else:
            qs = ImportBatch.objects.all()
        start = time()
        stats = recompute_interest_by_batch(qs)
        logger.info('Duration: %s, Stats: %s', time() - start, stats)
        logger.info('Query count: %d', len(connection.queries))
        for query in connection.queries:
            print(query)
