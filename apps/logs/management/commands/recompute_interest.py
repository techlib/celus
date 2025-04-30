import logging
from collections import Counter
from datetime import timedelta
from time import monotonic

from django.core.management.base import BaseCommand

from logs.logic.interest.computation import sync_interest_for_import_batch
from logs.models import ImportBatch, ReportType

logger = logging.getLogger(__name__)


def recompute_interest_by_batch(queryset=None):
    """
    This is a private copy of `recompute_interest_by_batch` from `logic.interest.computation`.
    It is slighly simplified and does not use import batch locking. It is indended for cases
    when we are sure that no other recomputations are happening - usually because celery etc.
    are switched off.

    The reason why locking is not used here is that with locking postgres takes loooong time
    to do the processing after the lock is released and transaction is committed. It also eats
    up a lot of memory during that time.
    """
    if queryset is None:
        queryset = ImportBatch.objects.filter(interest_timestamp__isnull=False)
    stats = Counter()
    total_count = queryset.count()
    logger.info("Going to recompute interest for %d batches", total_count)
    if total_count == 0:
        return stats
    interest_rt = ReportType.objects.get_interest_rt()
    start = monotonic()
    for i, import_batch in enumerate(queryset.iterator()):
        stats += sync_interest_for_import_batch(import_batch, interest_rt)
        if i and i % 100 == 0:
            logger.info(
                "Recomputed interest for %d out of %d batches (%.1f%%), elapsed: %s, ETA: %s, "
                "stats: %s",
                i,
                total_count,
                i * 100 / total_count,
                timedelta(seconds=monotonic() - start),
                timedelta(seconds=(monotonic() - start) / (i + 1) * (total_count - i)),
                stats,
            )
    return stats


class Command(BaseCommand):
    help = "Sync interest data"

    def add_arguments(self, parser):
        parser.add_argument("-p", dest="platform", help="short name of the platform to process")
        parser.add_argument(
            "-r", dest="report_type", help="short name of the report_type to process"
        )
        parser.add_argument("-f", dest="force", action="store_true", help="force recomputation")

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

        if options["force"]:
            qs.update(interest_timestamp=None)
        stats = recompute_interest_by_batch(qs)

        logger.info("Duration: %s, Stats: %s", monotonic() - start, stats)
        logger.info(
            "ImportBatches: %d; speed: %.1f ib/s", ib_count, ib_count / (monotonic() - start)
        )
