import logging
from time import time

from django.core.management.base import BaseCommand
from logs.logic.materialized_interest import sync_interest_by_import_batches
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
        stats = sync_interest_by_import_batches(qs)
        logger.info('Duration: %s, Stats: %s', time() - start, stats)
