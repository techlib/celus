"""
Stuff related to the artificial (materialized) report type 'interest' and its computation
"""
import logging
from collections import Counter
from time import time

from django.db.models import Sum, Count, Max, F
from django.db.transaction import atomic
from django.utils.timezone import now

from core.task_support import cache_based_lock
from logs.models import ReportType, AccessLog, DimensionText, ImportBatch

logger = logging.getLogger(__name__)


def sync_interest_by_import_batches(queryset=None) -> Counter:
    if not queryset:
        queryset = ImportBatch.objects.all()
    stats = Counter()
    interest_rt = ReportType.objects.get(short_name='interest')
    # we want to make sure that the ImportBatch has some accesslogs because otherwise it might
    # be that we caught it just after creation before any AccessLogs are added to it
    queryset = queryset.filter(interest_processed=False).\
        annotate(accesslog_count=Count('accesslog')).filter(accesslog_count__gt=0)
    total_count = queryset.count()
    logger.info('Found %d unprocessed import batches', total_count)
    start = time()
    for i, import_batch in enumerate(queryset):
        cur_stats = sync_interest_for_import_batch(import_batch, interest_rt)
        stats += cur_stats
        if time() - start > 10:
            logger.debug('Progress: %d/%d (%.1f %%)', i+1, total_count, 100.0*(i+1)/total_count)
            start = time()
    return stats


@atomic
def sync_interest_for_import_batch(
        import_batch: ImportBatch, interest_rt: ReportType) -> Counter:
    start = time()
    stats = Counter()
    # now we compute the interest data from it
    # go through the interest metrics and extract info about how to remap the values
    interest_metrics = []
    metric_remap = {}
    metric_to_ig = {}
    if import_batch.report_type not in import_batch.platform.interest_reports.all():
        # the report_type does not represent interest for this platform, we can skip it
        import_batch.interest_processed = True
        import_batch.interest_timestamp = now()
        import_batch.save()
        logger.debug('Import batch report type not in platform interest: %s - %s',
                     import_batch.report_type.short_name, import_batch.platform)
        return stats
    for rim in import_batch.report_type.reportinterestmetric_set.all().\
            select_related('interest_group'):
        if rim.target_metric_id:
            metric_remap[rim.metric_id] = rim.target_metric_id
        interest_metrics.append(rim.metric_id)
        metric_to_ig[rim.metric_id] = rim.interest_group
    # remap interest groups into DimensionText
    metric_to_dim1 = {}
    dim1 = interest_rt.dimensions_sorted[0]
    for metric_id, ig in metric_to_ig.items():
        dim_text, _created = DimensionText.objects.update_or_create(
            dimension=dim1, text=ig.short_name,
            defaults={'text_local_en': ig.name_en, 'text_local_cs': ig.name_cs})
        metric_to_dim1[metric_id] = dim_text.pk
    # get source data for the new logs
    new_logs = []
    # for the following dates, there are data for a superseeding report type, so we do not
    # want to created interest records for them
    clashing_dates = {}
    if import_batch.report_type.superseeded_by:
        clashing_dates = {
            x['date'] for x in
            import_batch.report_type.superseeded_by.accesslog_set.
            filter(platform_id=import_batch.platform_id,
                   organization_id=import_batch.organization_id).
            values('date')
        }
    for new_log_dict in import_batch.accesslog_set.filter(metric_id__in=interest_metrics).\
            exclude(date__in=clashing_dates).\
            values('organization_id', 'metric_id', 'platform_id', 'target_id', 'date').\
            annotate(value=Sum('value')).iterator():
        # deal with stuff related to the metric
        metric_id = new_log_dict['metric_id']
        # fill in dim1 based on the interest group of the metric
        new_log_dict['dim1'] = metric_to_dim1[metric_id]
        # remap metric to target metric if desired
        new_log_dict['metric_id'] = metric_remap.get(metric_id, metric_id)
        new_logs.append(new_log_dict)
    AccessLog.objects.bulk_create(
        AccessLog(report_type=interest_rt, import_batch=import_batch, **new_log)
        for new_log in new_logs)
    import_batch.interest_processed = True
    import_batch.interest_timestamp = now()
    import_batch.save()
    stats['new_logs'] += len(new_logs)
    logger.debug('Import took: %.2f s; Stats: %s', time()-start, stats)
    return stats


def remove_interest(queryset=None) -> Counter:
    if not queryset:
        queryset = ImportBatch.objects.all()
    stats = Counter()
    interest_rt = ReportType.objects.get(short_name='interest')
    for import_batch in queryset.filter(interest_processed=True):
        cur_stats = remove_interest_from_import_batch(import_batch, interest_rt)
        stats += cur_stats
        stats['import_batches'] += 1
    return stats


@atomic
def remove_interest_from_import_batch(import_batch: ImportBatch, interest_rt: ReportType) ->\
        Counter:
    deleted = import_batch.accesslog_set.filter(report_type=interest_rt).delete()
    import_batch.interest_processed = False
    import_batch.interest_timestamp = None
    import_batch.save()
    return Counter({'deleted_accesslogs': deleted[0]})


def recompute_interest_by_batch(queryset=None):
    with cache_based_lock('sync_interest_task'):
        # we share the lock with sync_interest_task because the two could compete for the
        # same data
        if not queryset:
            queryset = ImportBatch.objects.all()
        queryset = queryset.filter(interest_processed=True)
        interest_rt = ReportType.objects.get(short_name='interest')
        total_count = queryset.count()
        logger.info('Going to recompute interest for %d batches', total_count)
        for i, import_batch in enumerate(queryset.iterator()):
            remove_interest_from_import_batch(import_batch, interest_rt)
            sync_interest_for_import_batch(import_batch, interest_rt)
            if i % 20 == 0:
                logger.debug('Recomputed interest for %d out of %d batches', i, total_count)


def find_batches_that_need_interest_sync():
    # batches that do not have interest processed
    yield ImportBatch.objects.filter(interest_processed=False)
    yield ImportBatch.objects.filter(interest_timestamp__isnull=True)  # not likely, but may be
    # batches where interest definition changed after interest_timestamp
    yield ImportBatch.objects.all().\
        annotate(last_interest_change=Max('report_type__platforminterestreport__created')).\
        filter(last_interest_change__gte=F('interest_timestamp'))
