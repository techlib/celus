import logging
import sys
from time import time

from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from logs.logic.clickhouse import compare_db_with_clickhouse, deal_with_comparison_results

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = (
        'Compares the data from django db with configured clickhouse by importbatches and '
        'reports differences'
    )

    def add_arguments(self, parser):
        parser.add_argument('--fix-it', dest='fix_it', action='store_true')

    def handle(self, *args, **options):
        start = time()
        result = compare_db_with_clickhouse()

        logger.debug('Duration: %.2f s', time() - start)
        logger.info('Stats: %s', result.stats)
        if not result.is_ok():
            logger.error('FOUND DIFFERENCES BETWEEN DB AND CH!')
            logger.info('\n'.join(result.log))
            if options['fix_it']:
                logger.info('Fixing found problems')
                deal_with_comparison_results(result)
            sys.exit(100)

        logger.info('OK')
        sys.exit(0)
