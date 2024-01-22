"""
Intended to store all code needed to create and possibly update a database used for storing
logs. This is a separate clickhouse database.
"""
import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Make sure the logging database is up to date"

    def add_arguments(self, parser):
        parser.add_argument(
            "--drop-columns",
            action="store_true",
            help="When syncing table columns, also drop extra columns",
        )

    def handle(self, *args, **options):
        from django.conf import settings

        from core.request_logging.clickhouse import (
            CeleryTaskLogCube,
            RequestLogCube,
            get_logging_backend,
        )

        for name, cube, condition in (
            ("Request", RequestLogCube, settings.CLICKHOUSE_REQUEST_LOGGING),
            ("Celery task", CeleryTaskLogCube, settings.CLICKHOUSE_CELERY_TASK_LOGGING),
        ):
            if condition:
                backend = get_logging_backend()
                backend.initialize_storage(cube)
                changed, added, to_remove = backend.sync_storage(cube, drop=options["drop_columns"])
                if to_remove and not options["drop_columns"]:
                    logger.warning(
                        "Some columns are not present in the model anymore: %s. "
                        "Use --drop-columns to drop them.",
                        ", ".join(to_remove),
                    )
                if changed:
                    dropped = len(to_remove) if options["drop_columns"] else 0
                    logger.info(
                        f"{cube} schema was synced: %d columns added, %d dropped",
                        len(added),
                        dropped,
                    )
            else:
                logger.warning(f"{name} logging is disabled, skipping logging database creation")
