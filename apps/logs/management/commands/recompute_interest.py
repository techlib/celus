import logging
from time import monotonic

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from logs.logic.interest.computation import recompute_interest_by_batch
from logs.models import ImportBatch

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sync interest data"

    def add_arguments(self, parser):
        parser.add_argument("-p", dest="platform", help="short name of the platform to process")
        parser.add_argument(
            "-r", dest="report_type", help="short name of the report_type to process"
        )
        parser.add_argument("-f", dest="force", action="store_true", help="force recomputation")
        parser.add_argument("--verbose", dest="verbose", action="store_true")

    def handle(self, *args, **options):
        filters = {}
        if options["platform"]:
            filters["platform__short_name"] = options["platform"]
        if options["report_type"]:
            filters["report_type__short_name"] = options["report_type"]
        qs = ImportBatch.objects.filter(**filters)
        start = monotonic()
        ib_count = qs.count()
        logger.info("Going to recompute interest for %d ImportBatches", ib_count)
        with atomic():
            if options["force"]:
                qs.update(interest_timestamp=None)
            stats = recompute_interest_by_batch(qs, verbose=options["verbose"])

        logger.info("Duration: %s, Stats: %s", monotonic() - start, stats)
        logger.info(
            "ImportBatches: %d; speed: %.1f ib/s", ib_count, ib_count / (monotonic() - start)
        )
