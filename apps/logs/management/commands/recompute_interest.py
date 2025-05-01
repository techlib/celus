import itertools
import logging
from collections import Counter
from datetime import timedelta
from time import monotonic
from typing import List

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import F
from django.db.transaction import atomic
from django.utils.timezone import now
from organizations.models import Organization
from publications.models import Platform

from logs.cubes import AccessLogCube, ch_backend
from logs.logic.copy_from_saving import insert_new_accesslogs
from logs.logic.interest.computation import (
    InterestComputer,
    find_superseding_import_batches,
    recompute_interest_by_batch,
)
from logs.logic.materialized_reports import create_materialized_accesslogs_for_importbatches
from logs.models import AccessLog, ImportBatch, ReportType

logger = logging.getLogger(__name__)


def recompute_interest_force(queryset=None) -> Counter:
    """
    This is a private copy of `recompute_interest_by_batch` from `logic.interest.computation`.
    It is highly optimized and is indended for cases when we need very fast recomputation of
    interest and do not care that it may be slightly inconsistent in the meantime.

    It does not work on import batch basis, but rather groups them by organization, report type
    and platform, because then the interest definition is guaranteed to be the same for all
    batches in the group.

    We do not use one big lock on the whole queryset, because it may take too long to acquire
    and transaction may get too huge, which than causes postgresql to take loooong time to commit
    it. Instead, we lock by groups of organization, report type and platform.
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

    last_organization = None
    last_report_type = None

    for organization_id, report_type_id, platform_id in (
        queryset.order_by("organization", "report_type", "platform")
        .values_list("organization", "report_type", "platform")
        .distinct()
    ):
        organization = Organization.objects.get(id=organization_id)
        report_type = ReportType.objects.get(id=report_type_id)
        platform = Platform.objects.get(id=platform_id)

        logger.info(
            "Processing organization: %s, report_type: %s, platform: %s",
            organization,
            report_type,
            platform,
        )

        if last_organization != organization or last_report_type != report_type:
            computer = InterestComputer(interest_rt, organization, report_type)
            last_organization = organization
            last_report_type = report_type

        # we want to lock the import batches so that interest computation triggered in
        # celery tasks does not interfere with this command
        # we want to make sure all the import batches are processed, so we use a blocking
        # version of select_for_update
        ibs = ImportBatch.objects.filter(
            report_type=report_type, organization=organization, platform=platform
        )
        with atomic():
            ib_ids = list(ibs.values_list("pk", flat=True).select_for_update())  # locks the rows
            # delete the interest data from accesslog and clickhouse
            al_filters = {
                "report_type_id": interest_rt.pk,
                "organization_id": organization.pk,
                "platform_id": platform.pk,
                "import_batch_id__in": ib_ids,
            }
            logger.info("Deleting interest data from accesslog")
            AccessLog.objects.filter(**al_filters).delete(i_know_what_i_am_doing=True)
            ibs.update(interest_timestamp=None)

            new_stats = sync_interest_for_report_type_organization_platform(
                report_type, organization, platform, computer
            )
            # update clickhouse
            if settings.CLICKHOUSE_SYNC_ACTIVE:
                logger.info("Deleting interest data from clickhouse")
                ch_backend.delete_records(AccessLogCube.query().filter(**al_filters))
                logger.info("Adding interest data to clickhouse")
                add_interest_to_clickhouse(interest_rt, ib_ids)

        stats.update(new_stats)

        i = stats["import_batches"] + stats["superseded_import_batch"]
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


@atomic
def sync_interest_for_report_type_organization_platform(
    report_type: ReportType,
    organization: Organization,
    platform: Platform,
    interest_computer: "InterestComputer",
) -> Counter:
    """
    We assume no old interest data is present.

    Returns stats
    """
    stats = Counter()
    # check if superseding import batch exists and return empty list if it does
    date_to_superseding = find_superseding_import_batches(report_type, organization, platform)
    superseded_ibs = ImportBatch.objects.filter(
        report_type=report_type,
        organization=organization,
        platform=platform,
        date__in=date_to_superseding.keys(),
    )
    dealt_with = set()
    for superseded_ib in superseded_ibs:
        stats["superseded_import_batch"] += 1
        superseded_ib.interest_ib = date_to_superseding[superseded_ib.date]
        superseded_ib.save()
        dealt_with.add(superseded_ib.pk)

    # prepare the data
    import_batches = ImportBatch.objects.filter(
        report_type=report_type, organization=organization, platform=platform
    )
    logger.info("Import batches: %d", import_batches.count())
    if dealt_with:
        import_batches = import_batches.exclude(pk__in=dealt_with)
        logger.info("Import batches after excluding superseded: %d", import_batches.count())

    # extract interest from import batches
    start = monotonic()
    if settings.CLICKHOUSE_SYNC_ACTIVE:
        new_log_dicts = interest_computer.extract_interest_from_import_batches_ch(import_batches)
    else:
        new_log_dicts = interest_computer.extract_interest_from_import_batches(import_batches)
    logger.info("Extracted new log dicts: %d in %.2f s", len(new_log_dicts), monotonic() - start)
    # create new, remove old
    if new_log_dicts:
        insert_new_accesslogs(new_log_dicts, report_type_id=interest_computer.interest_rt.pk)
    # update the import batch
    import_batches.update(interest_timestamp=now(), interest_ib=F("pk"))

    stats["new_logs"] = len(new_log_dicts)
    stats["existing"] = 0
    stats["removed"] = 0
    stats["import_batches"] = import_batches.count()
    logger.debug("Import took: %.2f s; Stats: %s", monotonic() - start, stats)
    # potentially update materialized reports based on interest
    if new_log_dicts:
        for mat_rt in interest_computer.interest_rt.materialized_subreport_types:
            if added := create_materialized_accesslogs_for_importbatches(mat_rt, import_batches):
                ReportType.objects.filter(pk=mat_rt.pk).update(
                    approx_record_count=F("approx_record_count") + added
                )
    return stats


def add_interest_to_clickhouse(
    interest_rt: ReportType, import_batch_ids: List[int], batch_size=100_000, ib_batch_size=1_000
):
    """
    Add interest to clickhouse for the given import batch ids.
    """
    start = monotonic()
    to_write = []
    out = 0
    # postgres is not very good with large __in queries, so we iterate over the import batches
    # in batches of ib_batch_size. The 1k value was chosen empirically by testing on real data.
    # (similarly to the 100k batch size for the clickhouse bulk insert - btw. 1M eats too much RAM)
    iterator = iter(import_batch_ids)
    while batch := list(itertools.islice(iterator, ib_batch_size)):
        for al in (
            AccessLog.objects.filter(report_type=interest_rt, import_batch_id__in=batch)
            .values()
            .iterator()
        ):
            to_write.append(AccessLogCube.translate_accesslog_dict_to_cube(al))
            if len(to_write) >= batch_size:
                ch_backend.store_records(AccessLogCube, to_write)
                out += len(to_write)
                to_write = []
                logger.debug("Wrote %d records to clickhouse", out)
    if to_write:
        ch_backend.store_records(AccessLogCube, to_write)
        out += len(to_write)
    logger.info("Wrote %d records to clickhouse in %.2f s", out, monotonic() - start)
    return out


class Command(BaseCommand):
    help = "Sync interest data"

    def add_arguments(self, parser):
        parser.add_argument("-p", dest="platform", help="short name of the platform to process")
        parser.add_argument(
            "-r", dest="report_type", help="short name of the report_type to process"
        )
        parser.add_argument(
            "-o", dest="organization", help="short name of the organization to process"
        )
        parser.add_argument("-f", dest="force", action="store_true", help="force recomputation")

    def handle(self, *args, **options):
        filters = {}
        if options["platform"]:
            filters["platform_id"] = Platform.objects.get(short_name=options["platform"]).pk
        if options["report_type"]:
            filters["report_type_id"] = ReportType.objects.get(short_name=options["report_type"]).pk
        if options["organization"]:
            filters["organization_id"] = Organization.objects.get(
                short_name=options["organization"]
            ).pk

        qs = ImportBatch.objects.filter(**filters)
        start = monotonic()
        ib_count = qs.count()
        logger.info("Going to recompute interest for %d ImportBatches", ib_count)

        if options["force"]:
            # pre-delete all interest data
            stats = recompute_interest_force(qs)
        else:
            stats = recompute_interest_by_batch(qs)

        logger.info("Duration: %s, Stats: %s", monotonic() - start, stats)
        logger.info(
            "ImportBatches: %d; speed: %.1f ib/s", ib_count, ib_count / (monotonic() - start)
        )
