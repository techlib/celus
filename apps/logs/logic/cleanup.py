import logging
from collections import Counter
from random import shuffle
from typing import List, Set

from core.context_managers import needs_clickhouse_query
from django.conf import settings
from django.db.transaction import atomic
from hcube.api.models.aggregation import ArrayAgg as HArrayAgg
from hcube.api.models.aggregation import Count as HCount
from hcube.api.models.aggregation import Sum as HSum

from logs.cubes import AccessLogCube, ch_backend
from logs.logic.clickhouse import resync_import_batch_with_clickhouse
from logs.models import DIMENSION_COUNT, AccessLog, ImportBatch, OrganizationPlatform

logger = logging.getLogger(__name__)


def find_organizationplatform_differences() -> (Set, Set):
    ops = {
        tuple(rec)
        for rec in OrganizationPlatform.objects.all().values_list("organization_id", "platform_id")
    }
    logger.debug("Found %d OrganizationPlatform records", len(ops))
    ibs = {
        tuple(rec)
        for rec in ImportBatch.objects.all()
        .values_list("organization_id", "platform_id")
        .distinct()
    }
    logger.debug("Found %d ImportBatch records", len(ibs))

    missing = ibs - ops
    extra = ops - ibs
    return missing, extra


def fix_organizationplatform_differences(missing: Set, extra: Set):
    for org_id, platform_id in missing:
        OrganizationPlatform.objects.create(organization_id=org_id, platform_id=platform_id)
    for org_id, platform_id in extra:
        OrganizationPlatform.objects.filter(
            organization_id=org_id, platform_id=platform_id
        ).delete()


@needs_clickhouse_query
def find_split_accesslogs_with_the_same_title(fix_it: bool = False) -> Counter:
    """
    Finds records where due to title merging, accesslogs with the same key are present more
    than once in the database. When `fix_it` is True, the records are merged together.
    """
    stats = Counter()
    key_dims = [
        "platform_id",
        "metric_id",
        "organization_id",
        "target_id",
        "report_type_id",
        "date",
    ] + [f"dim{i + 1}" for i in range(DIMENSION_COUNT)]
    to_fix = []

    # we do it by batches of import_batches because the query would take too much memory
    # otherwise; we also shuffle the import_batches to get a more even distribution of the
    # import_batch sizes - this is because import_batches from the same platform tend to be
    # of similar size and also near each other in the database
    # The batch size can be adjusted in settings and has to be determined empirically to be a good
    # compromise between memory usage and speed. Values between 100 and 1000 seem reasonable.
    # Please note that the memory we are talking about here is the memory of the Clickhouse
    # server, not the memory of the Django process
    ib_ids = []
    ids = list(ImportBatch.objects.all().values_list("pk", flat=True))
    total = len(ids)
    shuffle(ids)
    logger.info("Total import batches: %d, batch size: %d", total, settings.SPLIT_LOGS_BATCH_SIZE)
    for i, ib_id in enumerate(ids):
        ib_ids.append(ib_id)
        if len(ib_ids) == settings.SPLIT_LOGS_BATCH_SIZE or i == total - 1:
            # the query below uses ArrayAgg for `import_batch_id`, but if fact it will always
            # have length 1. But ArrayAgg is the only way how to get the import_batch_id into
            # the result set.
            # The length is always 1 because we ensure on the import batch level, that there are
            # no clashing import batches. Thus, the "split" records will always come from the
            # same IB.
            query = (
                AccessLogCube.query()
                .filter(import_batch_id__in=ib_ids)
                .group_by(*key_dims)
                .aggregate(
                    count=HCount(),
                    ids=HArrayAgg(distinct="id"),
                    ibs=HArrayAgg(distinct="import_batch_id"),
                    sum=HSum("value"),
                )
                .group_filter(count__gt=1)
            )
            for rec in ch_backend.get_records(query):
                stats["ch duplicates"] += 1
                to_fix.append(rec)
            logger.info("Scanned IBs: %d; stats: %s", i + 1, stats)
            ib_ids = []

    ibs_to_resync = set()
    for rec in to_fix:
        ibs_to_resync |= set(rec.ibs)

    logger.info("Import batches to resync: %d", len(ibs_to_resync))

    als_to_update = {}
    als_to_delete: List[int] = []
    if fix_it:
        if ibs_to_resync:
            logger.info("Fixing...")
            for rec in to_fix:
                als_to_update[rec.ids[0]] = rec.sum
                als_to_delete.extend(rec.ids[1:])

            # update the values of the first record to the sum and delete the rest
            to_update = []
            logger.info(
                "Updating %d records and deleting %d", len(als_to_update), len(als_to_delete)
            )
            for al in AccessLog.objects.filter(pk__in=als_to_update.keys()):
                al.value = als_to_update[al.pk]
                to_update.append(al)
            with atomic():
                # batch_size was set to 500 because in production, trying to update 4k records
                # at once caused postgres to eat more than 8 GB or RAM and then crash with OOM
                AccessLog.objects.bulk_update(to_update, ["value"], batch_size=500)
                AccessLog.objects.filter(pk__in=als_to_delete).delete(i_know_what_i_am_doing=True)

            logger.info("Resyncing import batches with clickhouse")
            for i, ib in enumerate(ImportBatch.objects.filter(pk__in=ibs_to_resync)):
                logger.info("Resyncing IB #%d (%d / %d)", ib.pk, i + 1, len(ibs_to_resync))
                resync_import_batch_with_clickhouse(ib)
        else:
            logger.info("Nothing to fix")

    return stats
