import logging
from time import time

from django.core.management.base import BaseCommand

from logs.logic.materialized_reports import recompute_materialized_reports

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Recompute materialized reports for all import batches'

    def handle(self, *args, **options):
        start = time()
        stats = recompute_materialized_reports(
            progress_callback=lambda x: print(f'Done {x} batches')
        )
        logger.info('Duration: %s, Stats: %s', time() - start, stats)
