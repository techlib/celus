import logging
from time import monotonic, time
from typing import Callable, Iterable, Optional

from django.db.models import Count, FloatField, Q, QuerySet, Sum
from django.db.models.expressions import F, RawSQL
from django.db.models.functions import Cast
from django.db.transaction import atomic

from ..models import AccessLog, ImportBatch, ReportType

logger = logging.getLogger(__name__)


def sync_materialized_reports(report_type_qs: Optional[QuerySet[ReportType]] = None):
    """
    Create AccessLogs for all materialized report types. Uses `create_materialized_accesslogs`
    for smart synchronization of only unprocessed ImportBatches.
    :return:
    """
    qs = report_type_qs if report_type_qs is not None else ReportType.objects.all()
    for mat_rt in qs.only_materialized():
        if added := create_materialized_accesslogs(mat_rt):
            ReportType.objects.filter(pk=mat_rt.pk).update(
                approx_record_count=F("approx_record_count") + added
            )


def sync_materialized_reports_for_import_batch(ib: ImportBatch):
    """
    Create AccessLogs for all materialized report types for one import batch
    """
    interest_rt = ReportType.objects.get_interest_rt()
    for mat_rt in ReportType.objects.only_materialized().filter(
        materialization_spec__base_report_type__in=[ib.report_type, interest_rt]
    ):
        if added := create_materialized_accesslogs_for_importbatches(mat_rt, [ib]):
            ReportType.objects.filter(pk=mat_rt.pk).update(
                approx_record_count=F("approx_record_count") + added
            )


def create_materialized_accesslogs(rt: ReportType, batch_size=None) -> int:
    """
    Given an input materialized report type, it creates all the missing accesslogs. It detects
    what is missing by using data from individual ImportBatches.
    In order to save memory, it works repeatedly on batches of ImportBatches rather than on
    all of them at once.
    :param rt:
    :param batch_size: maximum number of ImportBatches to process at once, if None, we will guess
    :return:
    """
    assert rt.materialization_spec, "This code works only for materialized report types"
    if batch_size is None:
        batch_size = guess_batch_size_for_materialization(rt)
        logger.info('Guessing batch_size for "%s": %d', rt, batch_size)
    # construct query
    to_process = materialized_import_batch_queryset(rt)[:batch_size]
    total = 0
    while to_process:
        start = monotonic()
        size = create_materialized_accesslogs_for_importbatches(rt, to_process)
        logger.info(
            "Batch materialization took %.1f s; records created: %d", monotonic() - start, size
        )
        total += size
        to_process = materialized_import_batch_queryset(rt)[:batch_size]
    return total


def guess_batch_size_for_materialization(rt: ReportType, desired_log_threshold=25_000):
    """
    We guess how much data will be 'compressed' when doing materialization and try to guess
    the right size of input batches to generate a reasonable number of materialized AccessLogs
    so that we don't overload the memory with each batch.
    :param desired_log_threshold: The number of logs that should be created in one batch
    :param rt:
    :return:
    """
    keep, _remove = rt.materialization_spec.split_attributes(add_id_postfix=True)
    import_batch_qs = materialized_import_batch_queryset(rt)
    source_batch_count = import_batch_qs.count()
    if not source_batch_count:
        # shortcut for empty queryset
        return 1000
    # the annotation bellow causes group by to be run and Import batches counted
    # it is also faster than using distinct for some reason
    ibs = set(import_batch_qs.values_list("id", flat=True))
    result_log_count = (
        AccessLog.objects.filter(
            report_type=rt.materialization_spec.base_report_type, import_batch_id__in=ibs
        )
        .values("import_batch_id", *keep)
        .annotate(foo=Count("id"))
    )
    result_log_count = result_log_count.count()
    if source_batch_count and result_log_count:
        return source_batch_count * desired_log_threshold // result_log_count
    return 1000


@atomic
def create_materialized_accesslogs_for_importbatches(
    rt: ReportType, ibs: Iterable[ImportBatch]
) -> int:
    """
    Given an input materialized report type and a set of import batches, it creates all the
    materialized AccessLogs.
    :param rt:
    :param ibs: list or queryset of ImportBatches
    :return:
    """
    assert rt.materialization_spec, "This code works only for materialized report types"
    # remove existing materialized stuff from the ImportBatches
    # as we do not sync materialized report data to clickhouse, the code here does not
    # change anything from the clickhouse point of view
    ib_ids = {ib.id for ib in ibs}
    AccessLog.objects.filter(report_type=rt, import_batch__in=ib_ids).delete(
        i_know_what_i_am_doing=True
    )
    # construct query
    keep, _remove = rt.materialization_spec.split_attributes(add_id_postfix=True)
    query = (
        AccessLog.objects.filter(
            report_type=rt.materialization_spec.base_report_type, import_batch__in=ib_ids
        )
        .values("import_batch_id", *keep)
        .annotate(value=Sum("value"))
    )
    to_insert = [AccessLog(report_type=rt, **log) for log in query]
    AccessLog.objects.bulk_create(to_insert)
    for ib in ibs:
        ib.materialization_data[f"r{rt.pk}"] = time()
        ib.save(update_fields=["materialization_data"])
    return len(to_insert)


def materialized_import_batch_queryset(rt: ReportType) -> QuerySet:
    """
    Creates query attrs needed to get ImportBatches that should be 'materialized' for the
    ReportType rt.
    :param rt:
    :return: [Q]
    """
    if rt.materialization_spec.base_report_type.short_name == "interest":
        # for interest based materialized report types, we need to check the interest calculation
        # as well. We only include batches
        #  * with interest calculated already and not data materialization
        #  * with interest calculated after data materialization
        #    (can happen if interest definition is changed)
        # the interest_ts field will be added in annotation later on
        no_materialization = Q(
            **{f"materialization_data__r{rt.pk}__isnull": True}, interest_timestamp__isnull=False
        )
        stale_materialization = Q(
            interest_ts__gte=Cast(RawSQL("materialization_data->%s", (f"r{rt.pk}",)), FloatField())
        )
        updated_materialization = Q(
            **{f"materialization_data__r{rt.pk}__lt": rt.materialization_date.timestamp()}
        )
        # bellow we use RawSQL rather than Extract('interest_timestamp', 'epoch') because it
        # returns the timestamp in active timezone rather than in UTC as time() is presented
        # and thus even new data could appear stale due to the timezone shift :/
        return ImportBatch.objects.annotate(
            interest_ts=Cast(RawSQL("EXTRACT(EPOCH FROM interest_timestamp)", ()), FloatField())
        ).filter(stale_materialization | updated_materialization | no_materialization)
    else:
        no_materialization = Q(**{f"materialization_data__r{rt.pk}__isnull": True})
        updated_materialization = Q(
            **{f"materialization_data__r{rt.pk}__lt": rt.materialization_date.timestamp()}
        )
        return ImportBatch.objects.filter(no_materialization | updated_materialization)


@atomic
def remove_materialized_accesslogs(
    report_type_qs: Optional[QuerySet[ReportType]] = None,
    progress_callback: Callable[[int], None] = None,
):
    """
    Deletes all the AccessLogs for materialized views and associated data from ImportBatches
    :param report_type_qs: if provided, only the report types in the queryset will be processed
    :param progress_callback:
    :return:
    """
    rt_keys = set()
    # materialized reports are not synced with clickhouse, so the following delete has no
    # influence on clickhouse sync
    qs = report_type_qs if report_type_qs is not None else ReportType.objects.all()
    for rt in qs.only_materialized():
        rt.accesslog_set.all().delete(i_know_what_i_am_doing=True)
        rt_keys.add(rt.pk)
    # we iterate stupidly over all import batches, but that's life for you - I did not find
    # a way to batch update json field, so I at least go over each import batch only once for
    # all report types
    db_rt_keys = [f"r{rt_pk}" for rt_pk in rt_keys]
    for i, ib in enumerate(ImportBatch.objects.filter(materialization_data__has_keys=db_rt_keys)):
        save = False
        for key in db_rt_keys:
            if key in ib.materialization_data:
                ib.materialization_data.pop(key)
                save = True
        if save:
            ib.save()
        if progress_callback and i and i % 1000 == 0:
            progress_callback(i)


def recompute_materialized_reports(
    report_type_qs: Optional[QuerySet[ReportType]] = None,
    progress_callback: Callable[[int], None] = None,
):
    """
    Deletes all the AccessLogs for materialized views and associated data from ImportBatches
    and then restarts recomputation of materialized reports
    :param report_type_qs: if provided, only the report types in the queryset will be processed
    :param progress_callback: if provided, it will be called with the number of processed import
    batches
    :return:
    """
    remove_materialized_accesslogs(
        report_type_qs=report_type_qs, progress_callback=progress_callback
    )
    sync_materialized_reports(report_type_qs=report_type_qs)


def update_report_approx_record_count():
    """
    Synchronizes the `approx_record_count` values for all report types
    """
    for rt in ReportType.objects.all().annotate(record_count=Count("accesslog")):
        rt.approx_record_count = rt.record_count
        rt.save()
