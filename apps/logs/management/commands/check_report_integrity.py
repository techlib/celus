import logging
from collections import Counter
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Max, Min
from django.db.transaction import atomic
from sushi.models import SushiFetchAttempt

from logs.logic.custom_import import import_custom_data
from logs.models import AccessLog, DimensionText, ImportBatch, ManualDataUpload, ReportType
from logs.tasks import import_one_sushi_attempt_task

logger = logging.getLogger(__name__)


def convert_short_name(code: str, counter_version: int) -> str:
    """short_name conversion for Counter 5.1"""
    if counter_version == 51:
        return code + "51"
    else:
        return code


class Command(BaseCommand):
    help = (
        "Checks the integrity of individual report type dimensions - each dim column should "
        "contain only values which are present in the DimensionText model for that particular "
        "dimension"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "report_type_short_name",
            help="Report type short name(s), use 'all' to check all report types or comma-separated"
            " list for specific types",
        )
        parser.add_argument(
            "--fix-it",
            action="store_true",
            help="Fix the issue by reimporting the mismatched import batches",
        )
        parser.add_argument(
            "--force-fix",
            action="store_true",
            help="Force fix the issue by deleting the import batches if no reimport is possible",
        )

    @atomic
    def handle(self, *args, **options):
        stats = Counter()

        if options["report_type_short_name"] == "all":
            rt_list = ReportType.objects.all()
        else:
            short_names = [name.strip() for name in options["report_type_short_name"].split(",")]
            rt_list = ReportType.objects.filter(short_name__in=short_names)

        total_mismatched_ibs = set()
        for rt in rt_list:
            logger.info("%s:", rt.short_name)
            for dim in rt.dimensions_sorted:
                dim_values = DimensionText.objects.filter(dimension=dim).values_list(
                    "pk", flat=True
                )
                dim_attr = rt.dim_to_dim_attr(dim)
                mismatched = AccessLog.objects.exclude(**{f"{dim_attr}__in": dim_values}).filter(
                    report_type=rt, **{f"{dim_attr}__isnull": False}
                )
                count = mismatched.count()
                stats[dim.short_name] += count
                if count > 0:
                    mismatched_ibs = set(
                        mismatched.values_list("import_batch_id", flat=True).distinct()
                    )
                    logger.error("    %s: %d", dim.short_name, count)
                    logger.error(
                        "    Mismatched import batches (%d): %s",
                        len(mismatched_ibs),
                        mismatched_ibs,
                    )
                    total_mismatched_ibs.update(mismatched_ibs)
                else:
                    logger.info("    %s: %d", dim.short_name, count)

        if total_mismatched_ibs:
            logger.error("-- Issue found --")
            logger.error("Mismatched dimensions:")
            for dim_name, count in stats.items():
                if count > 0:
                    logger.error("    %s: %d", dim_name, count)

            logger.error(
                "Total mismatched import batches (%d): %s",
                len(total_mismatched_ibs),
                total_mismatched_ibs,
            )
            stats = ImportBatch.objects.filter(pk__in=total_mismatched_ibs).aggregate(
                min_created_at=Min("created"), max_created_at=Max("created")
            )
            logger.error(
                "Total mismatched import batches age range: %s - %s",
                stats["min_created_at"].date(),
                stats["max_created_at"].date(),
            )
            date_stats = Counter()
            for ib in ImportBatch.objects.filter(pk__in=total_mismatched_ibs):
                date_stats[ib.created.date()] += 1
            for date, count in date_stats.items():
                logger.error("    %s: %d", date, count)

        if total_mismatched_ibs and options["fix_it"]:
            stats = Counter()
            logger.error("Fixing the issue by reimporting the mismatched import batches")
            for ib in ImportBatch.objects.filter(pk__in=total_mismatched_ibs):
                logger.error(
                    "    %s: %s %s %s %s (%d)",
                    ib.pk,
                    ib.date,
                    ib.organization.name,
                    ib.platform.name,
                    ib.report_type.short_name,
                    ib.accesslog_set.count(),
                )
                attempt = SushiFetchAttempt.objects.filter(import_batch=ib).first()
                if attempt:
                    filepath = Path(settings.MEDIA_ROOT) / attempt.data_file.name
                    if filepath.exists():
                        import_one_sushi_attempt_task.delay(attempt.pk, reimport=True)
                        stats["reimported attempt"] += 1
                    else:
                        logger.error("    Data file not found for attempt %s", attempt.pk)
                        stats["no_data_file"] += 1
                else:
                    mdu = ManualDataUpload.objects.filter(import_batches=ib).first()
                    if mdu:
                        filepath = Path(settings.MEDIA_ROOT) / mdu.data_file.name
                        if filepath.exists():
                            import_custom_data(mdu, mdu.user)
                            stats["reimported mdu"] += 1
                        else:
                            logger.error("    Data file not found for import batch %s", ib.pk)
                            stats["no_data_file"] += 1
                    else:
                        size = ib.accesslog_set.count()
                        logger.error(
                            "    No attempt and no manual data upload found for import batch %s "
                            "(%d records)",
                            ib.pk,
                            size,
                        )
                        stats["no_attempt_and_mdu"] += 1
                        if options["force_fix"]:
                            ib.delete()
                            stats["deleted_ib"] += 1
                            logger.warning("    Deleted import batch %s", ib.pk)
                        else:
                            logger.warning("    use --force-fix to delete the import batch")
            logger.error("Stats: %s", stats)
