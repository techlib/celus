import logging
from time import time

from django.core.management.base import BaseCommand

from logs.logic.materialized_reports import recompute_materialized_reports
from logs.models import ReportType

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Recompute materialized reports for all import batches"

    def add_arguments(self, parser):
        rt_group = parser.add_mutually_exclusive_group(required=False)
        rt_group.add_argument(
            "-r",
            "--report-type",
            dest="report_type",
            type=str,
            help="Limit the recomputation to this materialized RT",
        )
        rt_group.add_argument(
            "-b",
            "--base-report",
            dest="base_report",
            type=str,
            help="Limit the recomputation to materialized reports for this base report",
        )

    def handle(self, *args, **options):
        start = time()
        if options["base_report"]:
            try:
                base = ReportType.objects.get(short_name=options["base_report"])
            except ReportType.DoesNotExist:
                raise ValueError(f'No such base report: {options["base_report"]}') from None
            qs = ReportType.objects.filter(materialization_spec__base_report_type=base)
        elif options["report_type"]:
            qs = ReportType.objects.filter(short_name=options["report_type"])
        else:
            qs = ReportType.objects.all()
        stats = recompute_materialized_reports(
            report_type_qs=qs, progress_callback=lambda x: print(f"Done {x} batches")
        )
        logger.info("Duration: %s, Stats: %s", time() - start, stats)
