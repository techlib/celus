import logging
from time import time

from core.middleware import QueryCounter
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

from logs.logic.materialized_reports import sync_materialized_reports
from logs.models import AccessLog, ImportBatch

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("import_batch_id", type=int, help="id of the import batch")
        parser.add_argument("--delete-only", action="store_true", help="Delete old data only")

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise RuntimeError("This command should only be run in DEBUG mode")
        logger.info("Deleting old data")
        ib = ImportBatch.objects.get(pk=options["import_batch_id"])
        AccessLog.objects.filter(
            import_batch=ib, report_type__materialization_spec__isnull=False
        ).delete(i_know_what_i_am_doing=True)
        ib.materialization_data = {}
        ib.save()
        if options["delete_only"]:
            return
        logger.info("Starting materialization")
        start = time()
        qc = QueryCounter(log_all=True)
        with connection.execute_wrapper(qc):
            sync_materialized_reports()
        logger.info("Materialization took %.1f s", time() - start)
