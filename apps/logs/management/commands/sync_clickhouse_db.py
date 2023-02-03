"""
Intended to store all code needed to create and possibly update the clickhouse database
used for storing accesslogs.
"""
import logging

from django.core.management.base import BaseCommand
from logs.cubes import AccessLogCube, create_ch_backend

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Make sure the clickhouse database is up to date'

    def add_arguments(self, parser):
        parser.add_argument(
            '--drop-columns',
            action='store_true',
            help='When syncing table columns, also drop extra columns',
        )

    def handle(self, *args, **options):
        from django.conf import settings

        if settings.CLICKHOUSE_SYNC_ACTIVE:
            # we want a fresh connection to clickhouse
            backend = create_ch_backend()
            backend.initialize_storage(AccessLogCube)
            changed, added, to_remove = backend.sync_storage(
                AccessLogCube, drop=options['drop_columns']
            )
            if to_remove and not options['drop_columns']:
                logger.warning(
                    'Some columns are not present in the model anymore: %s. '
                    'Use --drop-columns to drop them.',
                    ', '.join(to_remove),
                )
            if changed:
                dropped = len(to_remove) if options['drop_columns'] else 0
                logger.info(
                    'AccessLogCube schema was synced: %d columns added, %d dropped',
                    len(added),
                    dropped,
                )
        else:
            logger.warning('Clickhouse sync is disabled, skipping database sync')
