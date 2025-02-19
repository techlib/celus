"""
Stuff related to the artificial (materialized) report type 'interest' and its computation
"""

import logging
from collections import Counter
from time import monotonic, time
from typing import Dict, Iterable, List, Set

from django.conf import settings
from django.db.models import Count, Exists, F, Max, Min, OuterRef, Q, QuerySet, Subquery, Sum
from django.db.transaction import atomic, on_commit
from django.utils.timezone import now
from publications.models import Platform, PlatformInterestReport

from logs.constants import ACTION_INTEREST_CHANGE, ACTION_INTEREST_SMART_SYNC
from logs.logic.clickhouse import delete_interest_from_import_batches
from logs.logic.interest import get_interest_type_dim_from_interest_rt
from logs.logic.materialized_reports import sync_materialized_reports_for_import_batch
from logs.models import AccessLog, DimensionText, ImportBatch, LastAction, Metric, ReportType

# default COUNTER report types for interest
# `filters` are not used at the moment, they are just an idea for the future when we integrate
# IR fully and need them to distinguish between different types of interest from the same report
# This is why the `multimedia` interest from IR is commented out for now
INTEREST_DEFAULT_REPORT_TYPES = {
    (51, "IR"): {
        "interest": {
            "full_text": {
                "metrics": ["Total_Item_Requests"],
                "filters": [{"dimension": "Data_Type", "values": ["Multimedia"], "negate": True}],
            },
            # Multimedia interest uses the same metric as the full_text interest, and only differs
            # in the filter applied to it.
            # Because we do not support filters in the interest computation yet, we cannot use it.
            # Thus, multimedia interest is not computed from IR and IR_M1 has to be used
            #
            # "multimedia": {
            #     "metrics": ["Total_Item_Requests"],
            #     "filters": [{"dimension": "Data_Type", "values": ["Multimedia"]}],
            # },
            "full_text_denial": {
                "metrics": ["No_License", "Limit_Exceeded"],
                "filters": [{"dimension": "Data_Type", "values": ["Multimedia"], "negate": True}],
            },
        },
        "interest_metric_prefix": "C5.1",
    },
    (51, "TR"): {
        "interest": {
            "full_text": {"metrics": ["Total_Item_Requests"]},
            "full_text_denial": {"metrics": ["No_License", "Limit_Exceeded"]},
        },
        "superseded_by": (51, "IR"),
        "interest_metric_prefix": "C5.1",
    },
    (51, "DR"): {
        "interest": {
            "search": {"metrics": ["Searches_Regular"]},
            "search_denial": {"metrics": ["No_License", "Limit_Exceeded"]},
        },
        "interest_metric_prefix": "C5.1",
    },
    (5, "IR"): {
        "interest": {
            "full_text": {
                "metrics": ["Total_Item_Requests"],
                "filters": [{"dimension": "Data_Type", "values": ["Multimedia"], "negate": True}],
            },
            # Multimedia interest uses the same metric as the full_text interest, and only differs
            # in the filter applied to it.
            # Because we do not support filters in the interest computation yet, we cannot use it.
            # Thus, multimedia interest is not computed from IR and IR_M1 has to be used
            #
            # "multimedia": {
            #     "metrics": ["Total_Item_Requests"],
            #     "filters": [{"dimension": "Data_Type", "values": ["Multimedia"]}],
            # },
            "full_text_denial": {
                "metrics": ["No_License", "Limit_Exceeded"],
                "filters": [{"dimension": "Data_Type", "values": ["Multimedia"], "negate": True}],
            },
        },
        "superseded_by": (51, "IR"),
    },
    (5, "TR"): {
        "interest": {
            "full_text": {"metrics": ["Total_Item_Requests"]},
            "full_text_denial": {"metrics": ["No_License", "Limit_Exceeded"]},
        },
        # TR is superseded by both C51_TR and C5_IR, but we cannot express it right now,
        # it will have to wait for the new interest computation
        # for now, we use the C51_TR, because this will be used in production
        "superseded_by": (51, "TR"),
    },
    (5, "IR_M1"): {
        "interest": {"multimedia": {"metrics": ["Total_Item_Requests"]}}
        # IR_M1 would be superseded by IR, but we cannot compute multimedia interest from IR yet,
        # so we have to keep it as a separate report type for now
        # "superseded_by": (5, "IR"),
    },
    (5, "DR"): {
        "interest": {
            "search": {"metrics": ["Searches_Regular"]},
            "search_denial": {"metrics": ["No_License", "Limit_Exceeded"]},
        },
        "superseded_by": (51, "DR"),
    },
    (4, "JR1"): {
        "interest": {"full_text": {"metrics": ["FT Article Requests"]}},
        "superseded_by": (5, "TR"),
    },
    (4, "BR2"): {
        "interest": {"full_text": {"metrics": ["Book Section Requests"]}},
        "superseded_by": (5, "TR"),
    },
    (4, "DB1"): {
        "interest": {"search": {"metrics": ["Regular Searches"]}},
        "superseded_by": (5, "DR"),
    },
}

logger = logging.getLogger(__name__)


def sync_interest_by_import_batches(queryset=None) -> Counter:
    if not queryset:
        queryset = ImportBatch.objects.all()
    stats = Counter()
    interest_rt = ReportType.objects.get_interest_rt()
    # we want to make sure that the ImportBatch has some accesslogs because otherwise it might
    # be that we caught it just after creation before any AccessLogs are added to it
    queryset = (
        queryset.filter(interest_timestamp__isnull=True)
        .annotate(accesslog_count=Count("accesslog"))
        .filter(accesslog_count__gt=0)
    )
    total_count = queryset.count()
    logger.info("Found %d unprocessed import batches", total_count)
    start = time()
    for i, import_batch in enumerate(queryset):
        cur_stats = sync_interest_for_import_batch(import_batch, interest_rt)
        stats += cur_stats
        if time() - start > 10:
            logger.debug(
                "Progress: %d/%d (%.1f %%)", i + 1, total_count, 100.0 * (i + 1) / total_count
            )
            start = time()
    return stats


@atomic
def sync_interest_for_import_batch(
    import_batch: ImportBatch, interest_rt: ReportType, skip_clickhouse_sync=False
) -> Counter:
    start = time()
    stats = Counter()
    # prepare the data
    new_log_dicts = extract_interest_from_import_batch(import_batch, interest_rt)
    # compare it with existing data
    accesslog_keys = ("organization_id", "metric_id", "platform_id", "target_id", "item_id", "date")
    old_log_dicts = import_batch.accesslog_set.filter(report_type=interest_rt).values(
        "pk", *accesslog_keys
    )
    really_new, to_delete_pks, same = fast_compare_existing_and_new_records(
        old_log_dicts, new_log_dicts, accesslog_keys
    )
    # create new, remove old
    if really_new:
        AccessLog.objects.bulk_create(
            AccessLog(report_type=interest_rt, import_batch=import_batch, **log_dict)
            for log_dict in really_new
        )
    if to_delete_pks:
        AccessLog.objects.filter(pk__in=to_delete_pks).delete(i_know_what_i_am_doing=True)
    # update the import batch
    import_batch.interest_timestamp = now()
    import_batch.save()
    stats["new_logs"] = len(really_new)
    stats["existing"] = same
    stats["removed"] = len(to_delete_pks)
    logger.debug("Import took: %.2f s; Stats: %s", time() - start, stats)
    # potentially update materialized reports based on interest
    if really_new or to_delete_pks:
        sync_materialized_reports_for_import_batch(import_batch, interest_only=True)
    # sync with clickhouse
    if (
        settings.CLICKHOUSE_SYNC_ACTIVE
        and (really_new or to_delete_pks)
        and not skip_clickhouse_sync
    ):
        # we only sync with clickhouse if skip_clickhouse_sync is not set
        # It is used during data import is because it goes like this:
        #
        # 1. import normal data
        # 2. calculate interest
        # 3. prepare materialized reports
        # 4. sync with clickhouse
        #
        # so if we are in step 2, we do not want to sync interest with clickhouse
        # because it will be done later in step 4

        from .clickhouse import sync_import_batch_interest_with_clickhouse

        on_commit(lambda: sync_import_batch_interest_with_clickhouse(import_batch))
    return stats


def fast_compare_existing_and_new_records(
    old_records: List[Dict], new_records: List[Dict], compared_keys: Iterable, id_key="pk"
) -> (List[Dict], Set, int):
    """
    This code assumes that old_records have extra key `id_key` which is used to report back
    IDs of old_records that are to be removed (are not present in new_records).
    :return - List of records from new records that are new,
              set of IDs (`id_key`) of old records that are to be removed,
              number of records that are the same in old and new and do not need to be synced
    """
    old_tuple_to_pk = {
        tuple(old_record.get(key) for key in compared_keys): old_record.get(id_key)
        for old_record in old_records
    }
    same = 0
    seen_pks = set()
    really_new = []
    for new_record in new_records:
        new_tuple = tuple(new_record.get(key) for key in compared_keys)
        if new_tuple in old_tuple_to_pk:
            same += 1
            seen_pks.add(old_tuple_to_pk[new_tuple])
        else:
            really_new.append(new_record)
    obsolete_pks = set(old_tuple_to_pk.values()) - seen_pks
    return really_new, obsolete_pks, same


def extract_interest_from_import_batch(
    import_batch: ImportBatch, interest_rt: ReportType
) -> List[Dict]:
    """
    The return list contains dictionaries that contain data for accesslog creation,
    but without the report_type and import_batch fields
    """
    # now we compute the interest data from it
    # go through the interest metrics and extract info about how to remap the values
    interest_metrics = []
    metric_remap = {}
    metric_to_ig = {}
    # TODO: if we preselected the import_batches before submitting them here
    #       we could remove the whole test here, which create a query for each import batch
    if import_batch.report_type not in import_batch.platform.interest_reports.all():
        # the report_type does not represent interest for this platform, we can skip it
        logger.debug(
            "Import batch report type not in platform interest: %s - %s",
            import_batch.report_type.short_name,
            import_batch.platform,
        )
        return []
    for rim in import_batch.report_type.reportinterestmetric_set.all().select_related(
        "interest_group"
    ):
        if rim.target_metric_id:
            metric_remap[rim.metric_id] = rim.target_metric_id
        interest_metrics.append(rim.metric_id)
        metric_to_ig[rim.metric_id] = rim.interest_group
    # remap interest groups into DimensionText
    metric_to_it_dim = {}
    it_dim = get_interest_type_dim_from_interest_rt(interest_rt)
    for metric_id, ig in metric_to_ig.items():
        # we do not use update_or_create here, because it creates one select and one update
        # even if nothing has changed
        dim_text, _created = DimensionText.objects.get_or_create(
            dimension=it_dim,
            text=ig.short_name,
            defaults={"text_local_en": ig.name_en, "text_local_cs": ig.name_cs},
        )
        if dim_text.text_local_en != ig.name_en or dim_text.text_local_cs != ig.name_cs:
            dim_text.text_local_en = ig.name_en
            dim_text.text_local_cs = ig.name_cs
            dim_text.save()
        metric_to_it_dim[metric_id] = dim_text.pk
    # get source data for the new logs
    new_logs = []
    # for the following dates, there are data for a superseding report type, so we do not
    # want to created interest records for them
    clashing_dates = {}
    if import_batch.report_type.superseded_by:
        if hasattr(import_batch, "min_date") and hasattr(import_batch, "max_date"):
            # check if we have an annotated queryset and do not need to compute the min-max dates
            min_date = import_batch.min_date
            max_date = import_batch.max_date
        else:
            date_range = import_batch.accesslog_set.aggregate(
                min_date=Min("date"), max_date=Max("date")
            )
            min_date = date_range["min_date"]
            max_date = date_range["max_date"]
        if min_date and max_date:
            # the accesslog_set might be empty and then there is nothing that could be clashing
            clashing_dates = {
                x["date"]
                for x in import_batch.report_type.superseded_by.accesslog_set.filter(
                    platform_id=import_batch.platform_id,
                    organization_id=import_batch.organization_id,
                    date__lte=max_date,
                    date__gte=min_date,
                )
                .values("date")
                .distinct()
            }
    for new_log_dict in (
        import_batch.accesslog_set.filter(
            report_type=import_batch.report_type, metric_id__in=interest_metrics
        )
        .exclude(date__in=clashing_dates)
        .values("organization_id", "metric_id", "platform_id", "target_id", "item_id", "date")
        .annotate(value=Sum("value"))
        .iterator()
    ):
        # deal with stuff related to the metric
        metric_id = new_log_dict["metric_id"]
        # fill in dim1 based on the interest group of the metric
        new_log_dict["dim1"] = metric_to_it_dim[metric_id]
        # remap metric to target metric if desired
        new_log_dict["metric_id"] = metric_remap.get(metric_id, metric_id)
        new_logs.append(new_log_dict)
    return new_logs


def find_superseded_import_batches(import_batch: ImportBatch) -> QuerySet[ImportBatch]:
    """
    Find all import batches for which interest is superseded by the given import batch
    and thus need recomputation
    """
    if not PlatformInterestReport.objects.filter(
        platform_id=import_batch.platform_id, report_type_id=import_batch.report_type_id
    ).exists():
        # the import batch is not used for interest computation, so it cannot supersede anything
        return ImportBatch.objects.none()
    return ImportBatch.objects.filter(
        organization_id=import_batch.organization_id,
        platform_id=import_batch.platform_id,
        report_type__superseded_by=import_batch.report_type,
        date=import_batch.date,
    )


@atomic
def remove_interest_from_import_batches(
    import_batch_ids: [int], interest_rt: ReportType
) -> Counter:
    """
    Very efficient way how to remove interest records from multiple import batches.
    Deals with clickhouse as well.
    """
    deleted = AccessLog.objects.filter(
        report_type=interest_rt, import_batch_id__in=import_batch_ids
    ).delete(i_know_what_i_am_doing=True)
    logger.info("Deleted %d access logs for import batches %d", deleted[0], len(import_batch_ids))

    ImportBatch.objects.filter(pk__in=import_batch_ids).update(interest_timestamp=now())

    def delete_in_clickhouse():
        delete_interest_from_import_batches(interest_rt, import_batch_ids)

    if settings.CLICKHOUSE_SYNC_ACTIVE:
        on_commit(delete_in_clickhouse)
    return Counter({"deleted_accesslogs": deleted[0]})


@atomic
def recompute_interest_by_batch(queryset=None, verbose=False):
    """
    Using `verbose` reports potential discrepancies between old and recomputed interest values.
    It requires 2 extra queries for each import batch, so it should be used with caution.
    """
    # this function is run from two different parts of Celus:
    #
    # 1. when data is imported, interest is computed and some import batches are found
    #    where the interest may be obsoleted by the new data
    # 2. from `smart_interest_sync` which is run periodically to check if the interest is still
    #    up to date
    #
    # Because of this, we need to make sure that the recomputations from different sources do not
    # interfere with each other. This is done by using a lock on the import batches.

    if queryset is None:
        queryset = ImportBatch.objects.filter(interest_timestamp__isnull=False)
    # WARNING: the following messes up the queries when they are more complex and can
    #          lead to memory exhaustion - I leave it here as a memento against future attempts
    # queryset = queryset.select_related('report_type__superseded_by', 'platform').\
    #     annotate(min_date=Min('accesslog__date'), max_date=Max('accesslog__date'))
    stats = Counter()
    # lock all the import batches that are going to be recomputed
    queryset = queryset.select_for_update(skip_locked=True)
    total_count = queryset.count()
    logger.info("Going to recompute interest for %d batches", total_count)
    if total_count == 0:
        # short-circuit to save query for interest report type
        return stats
    interest_rt = ReportType.objects.get_interest_rt()
    for i, import_batch in enumerate(queryset.iterator()):
        old_sum = (
            import_batch.accesslog_set.filter(report_type=interest_rt).aggregate(sum=Sum("value"))[
                "sum"
            ]
            if verbose
            else 0
        )
        stats += sync_interest_for_import_batch(import_batch, interest_rt)
        if i % 100 == 0:
            logger.info(
                "Recomputed interest for %d out of %d batches, stats: %s", i, total_count, stats
            )
        if verbose:
            new_sum = import_batch.accesslog_set.filter(report_type=interest_rt).aggregate(
                sum=Sum("value")
            )["sum"]
            if new_sum != old_sum:
                logger.warning(
                    "Mismatched interest sum: %d vs %d (%.1f) [%s]",
                    old_sum,
                    new_sum,
                    old_sum / new_sum if old_sum and new_sum else 0,
                    import_batch,
                )
                stats["mismatch"] += 1
            else:
                stats["match"] += 1
    return stats


def smart_interest_sync():
    """
    Computes or recomputes interest for all import batches that need it - either are not
    processed yet or are out of sync
    """
    logger.debug("Smart syncing interest")
    for qs in find_batches_that_need_interest_recompute():
        # we need a simple query - recompute_interest_by_batch does locking and it is not
        # compatible with GROUP BY in the query
        ids = set(qs.values_list("pk", flat=True))
        recompute_interest_by_batch(queryset=ImportBatch.objects.filter(id__in=ids))
    logger.debug("Smart interest sync done, checking platform interests")
    stats = _check_platform_interests()
    logger.debug("Platform interest check done, stats: %s", stats)


@atomic
def _check_platform_interests() -> Counter:
    """
    If the platform interest has changed, then we do not need to recompute the actual values,
    but the interest in the batch should either be
    # - removed altogether
    #   (if the RT is no longer used for interest computation or superseding data exists)
    # - kept as is with the timestamp updated
    #   (if the RT is still used for interest computation, no superseding data found)
    # - created (if the RT was newly added to the platform)
    """
    start = monotonic()
    # platforms with updated interest
    p2rt = set(PlatformInterestReport.objects.values_list("platform_id", "report_type_id"))
    rt_superseding = {
        rt.pk: rt.superseded_by_id for rt in ReportType.objects.filter(superseded_by__isnull=False)
    }

    def get_ss_list(rt):
        ss_list = []
        while rt := rt_superseding.get(rt):
            ss_list.append(rt)
        return ss_list

    stats = Counter()
    interest_rt = ReportType.objects.get_interest_rt()
    ib_ids_to_update_timestamp = []
    ib_ids_to_remove_interest_from = []
    ib_ids_to_recompute_interest = []
    for i, ib in enumerate(
        ImportBatch.objects.all()
        .annotate(last_interest_change=Max("platform__platforminterestreport__last_modified"))
        .filter(Q(last_interest_change__gte=F("interest_timestamp")))
        .annotate(
            has_interest=Exists(
                AccessLog.objects.filter(report_type=interest_rt, import_batch_id=OuterRef("pk"))
            ),
            has_al=Exists(AccessLog.objects.filter(import_batch_id=OuterRef("pk"))),
        )
        .iterator()
    ):
        # all import batches where interest definition changed after interest_timestamp
        if (ib.platform_id, ib.report_type_id) not in p2rt:
            # the report type is not used for interest computation
            if ib.has_interest:
                ib_ids_to_remove_interest_from.append(ib.pk)
                stats["no longer interest"] += 1
            else:
                ib_ids_to_update_timestamp.append(ib.pk)
                stats["updated timestamp"] += 1
        elif (
            (ss_list := get_ss_list(ib.report_type_id))
            and (
                new_ibs := ImportBatch.objects.filter(
                    platform_id=ib.platform_id,
                    organization_id=ib.organization_id,
                    date=ib.date,
                    report_type_id__in=ss_list,
                )
            )
            # new_ibs must not be empty, otherwise they would not be considered superseding
            and (AccessLog.objects.filter(import_batch_id__in=new_ibs).exists())
        ):
            if ib.has_interest:
                logger.info("supersed list %s, ib.rt=%d", ss_list, ib.report_type_id)
                # superseding data exists, so we do not want to keep the interest
                ib_ids_to_remove_interest_from.append(ib.pk)
                stats["superseded interest"] += 1
            else:
                ib_ids_to_update_timestamp.append(ib.pk)
                stats["updated timestamp"] += 1
        elif ib.has_interest or not ib.has_al:
            # If the ib has data, there should be some interest here
            # because the actual computation of interest has not changed, we can keep the original
            # values and just update the timestamp
            # If there is no data, we do not need to compute interest - it would be zero anyway
            # So we just update the timestamp
            ib_ids_to_update_timestamp.append(ib.pk)
            stats["updated timestamp"] += 1
        else:
            # the IB has data but no interest, (and does not belong into the IBs which should not
            # have interest) -> we need to recompute the interest (typical if RT was newly connected
            # to platform)
            # this can produce some false positives in case where there is data, but no interest
            # represented by the data (e.g. the metrics in IB do not create interest). This does not
            # matter as it will be handled by the recompute_interest_by_batch with no harm done
            ib_ids_to_recompute_interest.append(ib.pk)
            stats["new interest"] += 1

        if i % 1000 == 0:
            logger.info("Processed %d import batches, stats: %s", i, stats)

    logger.info("Going to do the following interest updates: %s", stats)
    # remove interest from the import batches
    if ib_ids_to_remove_interest_from:
        remove_interest_from_import_batches(ib_ids_to_remove_interest_from, interest_rt)
    # recompute interest for the import batches
    if ib_ids_to_recompute_interest:
        recompute_interest_by_batch(ImportBatch.objects.filter(pk__in=ib_ids_to_recompute_interest))
    # update the timestamps
    if ib_ids_to_update_timestamp:
        ImportBatch.objects.filter(pk__in=ib_ids_to_update_timestamp).update(
            interest_timestamp=now()
        )

    logger.info("Check platform interest finished in %.2f s", monotonic() - start)
    return stats


def find_batches_that_need_interest_recompute():
    """
    Generator that returns querysets for different cases where ImportBatches may be out of
    sync with their interest data
    """
    interest_changed = LastAction.should_run(ACTION_INTEREST_SMART_SYNC, ACTION_INTEREST_CHANGE)
    for fn, only_if_interest_changed in (
        (_find_unprocessed_batches, False),
        (_find_metric_interest_changes, True),
        (_find_platform_report_type_disconnect, True),
        (_find_potentially_superseded_import_batches, False),
    ):
        if not only_if_interest_changed or interest_changed:
            yield fn()
    if interest_changed:
        for qs in _find_report_type_metric_disconnect():  # this is a generator itself
            yield qs
    # store the date of last interest sync to possibly skip it in the future
    LastAction.update_action(ACTION_INTEREST_SMART_SYNC)


def _find_unprocessed_batches():
    """batches that do not have interest processed"""
    return ImportBatch.objects.filter(interest_timestamp__isnull=True)


def _find_metric_interest_changes():
    """
    batches where interest definition changed after interest_timestamp - interestmetric change
    """
    return (
        ImportBatch.objects.all()
        .annotate(last_interest_change=Max("report_type__reportinterestmetric__last_modified"))
        .filter(last_interest_change__gte=F("interest_timestamp"))
    )


def _find_platform_report_type_disconnect():
    """
    batches where the platform and report_type are not (no longer) connected by
    PlatformInterestReport, but there are some interest data anyway
    """
    interest_rt = ReportType.objects.get_interest_rt()
    # platforms connected to a report_type referenced by its ID
    pir_platforms = Platform.objects.filter(
        platforminterestreport__report_type_id=OuterRef("report_type_id")
    ).values("pk")
    # access logs from one import batch and the interest report type
    access_log_query = AccessLog.objects.filter(
        report_type=interest_rt, import_batch=OuterRef("pk")
    ).values("pk")
    # only batches where platform is not amongst platforms that are referenced through
    # the report_type's PlatformInterestReport
    # limit to only those that do have interest stored
    query = (
        ImportBatch.objects.exclude(platform__in=Subquery(pir_platforms))
        .annotate(has_al=Exists(access_log_query))
        .filter(has_al=True)
    )
    return query


def _find_report_type_metric_disconnect():
    """
    batches where the report_type and metric are not (no longer) connected by
    ReportInterestMetric, but there are some interest data anyway
    """
    interest_rt = ReportType.objects.get_interest_rt()
    access_log_metric_query = (
        AccessLog.objects.filter(report_type=interest_rt, import_batch=OuterRef("pk"))
        .values("metric_id")
        .distinct()
    )
    # I could not find a way how to put this into one query as combining queries (such as union,
    # difference, etc.) are not supported in subqueries by Django (as of 2.2).
    # See this bug - https://code.djangoproject.com/ticket/29338
    for report_type in ReportType.objects.exclude(pk=interest_rt.pk):
        interest_metrics = (
            Metric.objects.filter(reportinterestmetric__report_type=report_type)
            .union(Metric.objects.filter(source_report_interest_metrics__report_type=report_type))
            .values("id")
        )
        query = (
            ImportBatch.objects.filter(report_type=report_type)
            .annotate(
                has_extra_metrics=Exists(
                    access_log_metric_query.exclude(metric_id__in=interest_metrics)
                )
            )
            .filter(has_extra_metrics=True)
        )
        yield query


def _find_superseded_import_batches():
    """
    Find import batches that have interest computed for superseded report_type and clashing
    data appeared with the superseding report_type

    WARNING: This works, but is incredibly slow as it does full scan of the AccessLog table;
             DO NOT USE IT!
    """
    logger.warning("This code is slooooow - do not use it")
    superseding_al = AccessLog.objects.filter(
        platform=OuterRef("platform"),
        organization=OuterRef("organization"),
        report_type=OuterRef("report_type__superseded_by"),
        date=OuterRef("date"),
    )
    al_query = (
        AccessLog.objects.filter(report_type__superseded_by__isnull=False)
        .annotate(has_clash=Exists(superseding_al))
        .filter(has_clash=True)
        .values("import_batch")
        .distinct()
    )
    interest_al = AccessLog.objects.filter(
        import_batch=OuterRef("pk"), report_type=ReportType.objects.get_interest_rt()
    )
    query = (
        ImportBatch.objects.filter(report_type__superseded_by__isnull=False)
        .annotate(has_interest=Exists(interest_al))
        .filter(has_interest=True, pk__in=al_query)
    )
    return query


def _find_potentially_superseded_import_batches():
    """
    Find import batches for which there may be a clashing import batch with report type
    superseding the one for this batch.

    NOTE: This potentially returns a large number of hits, but when run regularly, the update
          of interest_timestamp in the checked ImportBatches should keep the number at bay.
          If we ever wanted to get rid of this, we might store the date of the last interest
          calculation and only take import batches that have been created since. From these,
          we could then come up with a list of potentially obsoleted import batches.
    """
    superseding_ib = ImportBatch.objects.filter(
        platform=OuterRef("platform"),
        organization=OuterRef("organization"),
        report_type=OuterRef("report_type__superseded_by"),
        interest_timestamp__gt=OuterRef("interest_timestamp"),
    )
    query = (
        ImportBatch.objects.filter(report_type__superseded_by__isnull=False)
        .annotate(has_clash=Exists(superseding_ib))
        .filter(has_clash=True)
    )
    return query
