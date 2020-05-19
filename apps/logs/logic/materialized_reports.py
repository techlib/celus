import logging
from time import time
from typing import Iterable, Dict

from django.db.models import Sum
from django.db.transaction import atomic

from organizations.logic.queries import extend_query_filter
from ..models import ImportBatch, AccessLog, ReportType

logger = logging.getLogger(__name__)


def sync_materialized_reports():
    """
    Create AccessLogs for all materialized report types. Uses `create_materialized_accesslogs`
    for smart synchronization of only unprocessed ImportBatches.
    :return:
    """
    for mat_rt in ReportType.objects.filter(materialization_spec__isnull=False):
        create_materialized_accesslogs(mat_rt)


def create_materialized_accesslogs(rt: ReportType, batch_size=None):
    """
    Given an input materialized report type, it creates all the missing accesslogs. It detects
    what is missing by using data from individual ImportBatches.
    In order to save memory, it works repeatedly on batches of ImportBatches rather than on
    all of them at once.
    :param rt:
    :param batch_size: maximum number of ImportBatches to process at once, if None, we will guess
    :return:
    """
    assert rt.materialization_spec, 'This code works only for materialized report types'
    if batch_size is None:
        batch_size = guess_batch_size_for_materialization(rt)
        logger.debug('Guessing batch_size for "%s": %d', rt, batch_size)
    # construct query
    filter_attrs = materialized_import_batch_query_attrs(rt)
    to_process = ImportBatch.objects.filter(**filter_attrs)[:batch_size]
    while to_process:
        start = monotonic()
        create_materialized_accesslogs_for_importbatches(rt, to_process)
        logger.debug('Batch materialization took %.1f s', monotonic() - start)
        to_process = ImportBatch.objects.filter(**filter_attrs)[:batch_size]


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
    import_batch_filter = materialized_import_batch_query_attrs(rt)
    source_batch_count = ImportBatch.objects.filter(**import_batch_filter).count()
    result_log_count = (
        AccessLog.objects.filter(
            report_type=rt.materialization_spec.base_report_type,
            **extend_query_filter(import_batch_filter, 'import_batch__'),
        )
        .values('import_batch_id', *keep)
        .annotate(value=Sum('value'))
        .count()
    )
    if source_batch_count and result_log_count:
        return source_batch_count * desired_log_threshold // result_log_count
    return 1000


@atomic
def create_materialized_accesslogs_for_importbatches(rt: ReportType, ibs: Iterable[ImportBatch]):
    """
    Given an input materialized report type and a set of import batches, it creates all the
    materialized AccessLogs.
    :param rt:
    :param ibs: list or queryset of ImportBatches
    :return:
    """
    assert rt.materialization_spec, 'This code works only for materialized report types'
    # remove existing materialized stuff from the ImportBatches
    AccessLog.objects.filter(report_type=rt, import_batch__in=ibs).delete()
    # construct query
    keep, _remove = rt.materialization_spec.split_attributes(add_id_postfix=True)
    query = (
        AccessLog.objects.filter(
            report_type=rt.materialization_spec.base_report_type, import_batch__in=ibs
        )
        .values('import_batch_id', *keep)
        .annotate(value=Sum('value'))
    )
    AccessLog.objects.bulk_create(AccessLog(report_type=rt, **log) for log in query)
    for ib in ibs:
        ib.materialization_data[f'r{rt.pk}'] = time()
        ib.save(update_fields=['materialization_data'])


def materialized_import_batch_query_attrs(rt: ReportType) -> Dict:
    """
    Creates query attrs needed to get ImportBatches that should be 'materialized' for the
    ReportType rt.
    :param rt:
    :return: {}
    """
    filter_attrs = {f'materialization_data__r{rt.pk}__isnull': True}
    if rt.materialization_spec.base_report_type.short_name == 'interest':
        # for interest based materialized report types, we need to check the interest calculation
        # as well
        filter_attrs['interest_timestamp__isnull'] = False
    return filter_attrs
