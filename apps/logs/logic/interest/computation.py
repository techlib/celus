"""
Stuff related to the artificial (materialized) report type 'interest' and its computation
"""

import logging
from collections import Counter, defaultdict
from functools import lru_cache
from time import time
from typing import Dict, Iterable, List, Optional, Set, Tuple

from django.conf import settings
from django.db.models import Case, Count, Exists, F, Max, OuterRef, Q, QuerySet, Sum, Value, When
from django.db.transaction import atomic, on_commit
from django.utils.timezone import now

from logs.constants import ACTION_INTEREST_CHANGE, ACTION_INTEREST_SMART_SYNC
from logs.logic.clickhouse import delete_interest_from_import_batches
from logs.logic.interest.definitions import INTEREST_EXTRA_DIMENSIONS
from logs.logic.materialized_reports import sync_materialized_reports_for_import_batch
from logs.models import (
    AccessLog,
    Dimension,
    DimensionText,
    ImportBatch,
    InterestDimensionValueMapping,
    InterestGroup,
    InterestProfile,
    LastAction,
    Metric,
    ReportType,
)

# default COUNTER report types for interest
# 'metrics' is a dict mapping the metric to the interest profile short_name,
# if the interest profile is not given, the metric will be used regardless of profile

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
    interest_computer = InterestComputer(interest_rt)
    start = time()
    for i, import_batch in enumerate(queryset):
        cur_stats = sync_interest_for_import_batch(
            import_batch, interest_rt, interest_computer=interest_computer
        )
        stats += cur_stats
        if time() - start > 10:
            logger.debug(
                "Progress: %d/%d (%.1f %%)", i + 1, total_count, 100.0 * (i + 1) / total_count
            )
            start = time()
    return stats


@atomic
def sync_interest_for_import_batch(
    import_batch: ImportBatch,
    interest_rt: ReportType,
    skip_clickhouse_sync=False,
    interest_computer: Optional["InterestComputer"] = None,
) -> Counter:
    """
    Passing InterestComputer is an optimization because it caches some data from the DB
    thus reducing the number of DB queries.
    """
    start = time()
    stats = Counter()
    # check if superseding import batch exists and return empty list if it does
    if superseding_ib := find_superseding_import_batch(import_batch):
        stats["superseded_import_batch"] += 1
        import_batch.interest_ib = superseding_ib
        remove_interest_from_import_batches([import_batch.pk], interest_rt)  # remove old interest
        import_batch.save()
        return stats

    # prepare the data
    ic = interest_computer or InterestComputer(interest_rt)
    new_log_dicts = ic.extract_interest_from_import_batch(import_batch)
    # compare it with existing data
    accesslog_keys = (
        "organization_id",
        "metric_id",
        "platform_id",
        "target_id",
        "item_id",
        "date",
        *interest_rt.explicit_dimensions,
    )
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
    import_batch.interest_ib = import_batch  # not superseded by anything, reference to itself
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

        from ..clickhouse import sync_import_batch_interest_with_clickhouse

        on_commit(lambda: sync_import_batch_interest_with_clickhouse(import_batch))
    return stats


def find_superseding_import_batch(import_batch: ImportBatch) -> Optional[ImportBatch]:
    """
    Find the superseding import batch for the given import batch.
    """
    superseding_report_types = get_report_type_superseding_report_types(import_batch.report_type)
    ibs = list(
        ImportBatch.objects.filter(
            report_type__in=superseding_report_types,
            organization_id=import_batch.organization_id,
            platform_id=import_batch.platform_id,
            date=import_batch.date,
        )
    )
    if not ibs:
        return None
    if len(ibs) == 1:
        return ibs[0]
    # if there are multiple, return the one which RT occurs first
    ib_rts = {ib.report_type_id for ib in ibs}
    for rt in superseding_report_types:
        if rt.id in ib_rts:
            return next(ib for ib in ibs if ib.report_type_id == rt.id)
    raise ValueError("This should never happen - no superseding import batch found")


def get_report_type_superseding_report_types(report_type: ReportType) -> List[ReportType]:
    """
    Returns a list of report types that supersede the given report type
    """
    id_to_superseding_rt = {
        rt.id: rt.superseded_by
        for rt in ReportType.objects.filter(superseded_by__isnull=False).select_related(
            "superseded_by"
        )
    }
    superseding_rts = []
    while report_type := id_to_superseding_rt.get(report_type.id):
        if report_type not in superseding_rts:
            superseding_rts.append(report_type)
        else:
            logger.warning("Cycle in report type hierarchy: %s", report_type)
            break
    superseding_rts.reverse()  # the first one should be the highest in the hierarchy
    return superseding_rts


def get_report_types_superseded_by_report_type(report_type: ReportType) -> List[ReportType]:
    """
    Returns a list of report types that are superseded by the given report type
    """
    id_to_superseded = defaultdict(list)
    for rt in ReportType.objects.filter(superseded_by__isnull=False).select_related(
        "superseded_by"
    ):
        id_to_superseded[rt.superseded_by_id].append(rt)
    out = list(id_to_superseded.get(report_type.id, []))  # copy the list
    newly_added = set(out)
    while newly_added:
        rt = newly_added.pop()
        for new_rt in id_to_superseded.get(rt.id, []):
            if new_rt not in out:
                out.append(new_rt)
                newly_added.add(new_rt)
    return out


def fast_compare_existing_and_new_records(
    old_records: List[Dict], new_records: List[Dict], compared_keys: Iterable, id_key="pk"
) -> Tuple[List[Dict], Set, int]:
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


def find_superseded_import_batches(import_batch: ImportBatch) -> QuerySet[ImportBatch]:
    """
    Find all import batches for which interest is superseded by the given import batch
    and thus need recomputation
    """
    superseded_rts = get_report_types_superseded_by_report_type(import_batch.report_type)
    return ImportBatch.objects.filter(
        organization_id=import_batch.organization_id,
        platform_id=import_batch.platform_id,
        report_type__in=superseded_rts,
        date=import_batch.date,
    )


class InterestComputer:
    """
    Computes interest for a given import batch. An instance can be reused for multiple
    import batches, thus providing some caching.
    """

    # When computing values for dimX for interest, the dimension names may clash
    # with the original accesslog dimensions.
    # To avoid this, we prefix the dimension names with this string. We strip it
    # when post-processing the accesslog data in `extract_interest_from_import_batch`
    EXTRA_DIM_PREFIX = "XX_"

    def __init__(self, interest_rt: ReportType):
        self.interest_rt = interest_rt

        self.rt_dim = self.interest_rt.dim_name_to_dim_attr("Original_Report_Type")
        self.metric_dim = self.interest_rt.dim_name_to_dim_attr("Original_Metric")

    def extract_interest_from_import_batch(self, import_batch: ImportBatch) -> List[Dict]:
        """
        The return list contains dictionaries that contain data for accesslog creation,
        but without the report_type and import_batch fields
        """
        new_logs = []
        interest_profile = import_batch.organization.get_interest_profile()
        annotations = self.prepare_report_type_interest_dimensions(
            import_batch.report_type, self.interest_rt
        )
        orig_rt_text = self.get_orig_rt_text(import_batch.report_type)

        for metric, ig, filters in self.get_interest_definitions(
            interest_profile, import_batch.report_type
        ):
            orig_metric_text = self.get_orig_metric_text(metric)

            qs = (
                import_batch.accesslog_set.filter(
                    *filters, report_type=import_batch.report_type, metric_id=metric.id
                )
                .annotate(**annotations)
                .values(
                    "organization_id",
                    "metric_id",
                    "platform_id",
                    "target_id",
                    "item_id",
                    "date",
                    *annotations.keys(),
                )
                .annotate(value=Sum("value"))
            )

            for new_log_dict in qs:
                # rt_dim is the original report type dimension
                if self.rt_dim:
                    new_log_dict[self.rt_dim] = orig_rt_text.pk
                # metric_dim is the original metric dimension
                if self.metric_dim:
                    new_log_dict[self.metric_dim] = orig_metric_text.pk

                # strip X from the keys
                for key in list(new_log_dict.keys()):
                    if key.startswith(self.EXTRA_DIM_PREFIX):
                        new_log_dict[key[len(self.EXTRA_DIM_PREFIX) :]] = new_log_dict.pop(key)

                # metric is the one defined by the interest group
                new_log_dict["metric_id"] = ig.metric_id
                new_logs.append(new_log_dict)
        return new_logs

    @lru_cache(maxsize=100)  # noqa: B019, I know what I am doing
    def get_orig_rt_text(self, report_type: ReportType) -> DimensionText:
        """
        Returns the original report type text for the given report type and dimension name
        """
        defaults = {}
        for lang in [lng[0] for lng in settings.LANGUAGES]:
            defaults[f"text_local_{lang}"] = getattr(report_type, f"name_{lang}")
        return DimensionText.objects.get_or_create(
            dimension=self.interest_rt.dimension_by_attr_name(self.rt_dim),
            text=report_type.short_name,
            defaults=defaults,
        )[0]

    @lru_cache(maxsize=100)  # noqa: B019, I know what I am doing
    def get_orig_metric_text(self, metric: Metric) -> DimensionText:
        """
        Returns the original metric text for the given metric and dimension name
        """
        defaults = {}
        for lang in [lng[0] for lng in settings.LANGUAGES]:
            defaults[f"text_local_{lang}"] = getattr(metric, f"name_{lang}")
        return DimensionText.objects.get_or_create(
            dimension=self.interest_rt.dimension_by_attr_name(self.metric_dim),
            text=metric.short_name,
            defaults=defaults,
        )[0]

    @classmethod
    @lru_cache(maxsize=100)  # noqa: B019, I know what I am doing
    def prepare_report_type_interest_dimensions(
        cls, report_type: ReportType, interest_rt: ReportType
    ) -> Dict[str, Case]:
        """
        Returns a mapping between interest dimensions and original accesslog dimensions
        """
        out = {}
        for dim_name in INTEREST_EXTRA_DIMENSIONS:
            dim = Dimension.objects.get(short_name=dim_name)

            if not (
                idvm := InterestDimensionValueMapping.objects.filter(
                    Q(source_rtdim__report_type=report_type) | Q(source_rtdim__isnull=True),
                    interest_rtdim__report_type=interest_rt,
                    interest_rtdim__dimension=dim,
                )
                .order_by(F("source_rtdim__report_type").desc(nulls_last=True))
                .first()
            ):
                raise ValueError(f"No mapping found for dimension {dim_name}")

            whens = []
            for dest_name, src_names in idvm.mapping.items():
                dest_value = DimensionText.objects.get_or_create(
                    dimension=idvm.interest_rtdim.dimension, text=dest_name
                )[0].pk
                src_values = [
                    DimensionText.objects.get_or_create(
                        dimension=idvm.source_rtdim.dimension, text=src_name
                    )[0].pk
                    for src_name in src_names
                ]

                dim_attr = report_type.dim_to_dim_attr(idvm.source_rtdim.dimension)
                logger.debug("Mapping: %s: %s -> %s", dim_attr, src_values, dest_value)
                whens.append(When(**{f"{dim_attr}__in": src_values}, then=Value(dest_value)))
            default = DimensionText.objects.get_or_create(
                dimension=idvm.interest_rtdim.dimension, text=idvm.default_value
            )[0].pk
            out[
                cls.EXTRA_DIM_PREFIX + interest_rt.dim_to_dim_attr(idvm.interest_rtdim.dimension)
            ] = Case(*whens, default=Value(default))
        return out

    @classmethod
    def get_interest_definitions(
        cls, interest_profile: InterestProfile, report_type: ReportType
    ) -> List[Tuple[Metric, InterestGroup, List]]:
        """
        Returns a list of tuples that contain the metric, interest group and a dictionary of
        filters that define the interest.
        """
        out = []
        for rim in report_type.reportinterestmetric_set.filter(
            Q(interest_profile=interest_profile) | Q(interest_profile__isnull=True)
        ).select_related("metric", "interest_group"):
            fltrs = []
            for fltr in rim.filters.all():
                dim_attr = report_type.dim_to_dim_attr(fltr.dimension)
                q = Q(
                    **{
                        f"{dim_attr}__in": DimensionText.objects.filter(
                            dimension=fltr.dimension, text__in=fltr.values
                        ).values_list("pk", flat=True)
                    }
                )
                if fltr.negated:
                    q = ~q
                fltrs.append(q)
            out.append((rim.metric, rim.interest_group, fltrs))
        return out


@atomic
def remove_interest_from_import_batches(
    import_batch_ids: List[int], interest_rt: ReportType
) -> Counter:
    """
    Very efficient way how to remove interest records from multiple import batches.
    Deals with clickhouse as well.
    """
    rt_ids = ReportType.objects.filter(
        materialization_spec__base_report_type=interest_rt
    ).values_list("pk", flat=True)
    deleted = AccessLog.objects.filter(
        report_type__in=[interest_rt.pk, *rt_ids], import_batch_id__in=import_batch_ids
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


def find_batches_that_need_interest_recompute():
    """
    Generator that returns querysets for different cases where ImportBatches may be out of
    sync with their interest data
    """
    interest_changed = LastAction.should_run(ACTION_INTEREST_SMART_SYNC, ACTION_INTEREST_CHANGE)
    for fn, only_if_interest_changed in (
        (_find_unprocessed_batches, False),
        (_find_orphan_superseded_batches, False),
        (_find_metric_interest_changes, True),
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


def _find_orphan_superseded_batches():
    """
    batches that were superseded by another batch, but the superseding batch was deleted
    """
    return ImportBatch.objects.filter(interest_ib__isnull=True)


def _find_metric_interest_changes():
    """
    batches where interest definition changed after interest_timestamp - interestmetric change
    """
    return (
        ImportBatch.objects.all()
        .annotate(last_interest_change=Max("report_type__reportinterestmetric__last_modified"))
        .filter(last_interest_change__gte=F("interest_timestamp"))
    )


def _find_report_type_metric_disconnect():
    """
    batches where the report_type and metric are not (no longer) connected by
    ReportInterestMetric, but there are some interest data anyway
    """
    interest_rt = ReportType.objects.get_interest_rt()
    orig_metric_dim_attr = interest_rt.dim_name_to_dim_attr("Original_Metric")
    orig_metric_dim = interest_rt.dimension_by_attr_name(orig_metric_dim_attr)
    access_log_metric_query = (
        AccessLog.objects.filter(report_type=interest_rt, import_batch=OuterRef("pk"))
        .values("metric_id")
        .distinct()
    )
    # I could not find a way how to put this into one query as combining queries (such as union,
    # difference, etc.) are not supported in subqueries by Django (as of 2.2).
    # See this bug - https://code.djangoproject.com/ticket/29338
    for report_type in ReportType.objects.exclude(pk=interest_rt.pk):
        interest_metrics = Metric.objects.filter(
            reportinterestmetric__report_type=report_type
        ).values_list("short_name", flat=True)
        dim_values = DimensionText.objects.filter(
            dimension=orig_metric_dim, text__in=interest_metrics
        ).values_list("pk", flat=True)
        query = (
            ImportBatch.objects.filter(report_type=report_type)
            .annotate(
                has_extra_metrics=Exists(
                    access_log_metric_query.exclude(**{f"{orig_metric_dim_attr}__in": dim_values})
                )
            )
            .filter(has_extra_metrics=True)
        )
        yield query


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
