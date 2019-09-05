"""
Stuff related to the artificial (materialized) report type 'interest' and its computation
"""
from datetime import datetime
import logging
from collections import Counter
from time import time

from django.db.models import Max, Sum
from django.db.transaction import atomic

from logs.models import ReportType, AccessLog, DimensionText, ImportBatch
from publications.models import Platform


logger = logging.getLogger(__name__)


def sync_interest_for_platform(platform: Platform) -> Counter:
    stats = Counter()
    interest_rt = ReportType.objects.get(short_name='interest')
    # we need to get the threshold date here because once we add new interest AccessLogs
    # into the database, the date would change and no more changes will be detected
    newest_interest = AccessLog.objects.filter(report_type=interest_rt, platform=platform).\
        aggregate(newest=Max('created'))['newest']
    for rt in platform.interest_reports.all():
        logger.debug('Starting interest sync for "%s" and report type "%s"', platform, rt)
        cur_stats = sync_interest_for_platform_and_report_type(platform, rt, interest_rt,
                                                               newest_interest)
        logger.debug('Interest sync stats: %s', cur_stats)
        stats += cur_stats
    return stats


@atomic
def sync_interest_for_platform_and_report_type(
        platform: Platform, report_type: ReportType, interest_rt: ReportType,
        threshold_time:datetime = None) -> Counter:
    start = time()
    # we find the accesslogs for the report_type and platform at hand that are newer
    # than the threshold_time (if given)
    candidates = AccessLog.objects.filter(platform=platform, report_type=report_type)
    if threshold_time:
        candidates = candidates.filter(created__gte=threshold_time)
    if candidates.count() == 0:
        return Counter()
    print('#1', time() - start)
    # now we compute the interest data from it
    # go through the interest metrics and extract info about how to remap the values
    interest_metrics = []
    metric_remap = {}
    metric_to_ig = {}
    for rim in report_type.reportinterestmetric_set.all().select_related('interest_group'):
        if rim.target_metric_id:
            metric_remap[rim.metric_id] = rim.target_metric_id
        interest_metrics.append(rim.metric_id)
        metric_to_ig[rim.metric_id] = rim.interest_group
    print('#2', time() - start)
    # remap interest groups into DimensionText
    metric_to_dim1 = {}
    dim1 = interest_rt.dimensions_sorted[0]
    for metric_id, ig in metric_to_ig.items():
        dim_text, _created = DimensionText.objects.update_or_create(
            dimension=dim1, text=ig.short_name,
            defaults={'text_local_en': ig.name_en, 'text_local_cs': ig.name_cs})
        metric_to_dim1[metric_id] = dim_text.pk
    print('#3', time() - start)
    # get source data for the new logs
    # we split processing into months so that if there are many candidates,
    # we do not run out of memory
    months = [x['date'] for x in
              candidates.filter(metric_id__in=interest_metrics).values('date').distinct()]
    print('#3.1', time() - start)
    stats = Counter()
    key_keys = ['organization_id', 'metric_id', 'platform_id', 'target_id', 'date', 'dim1']
    for month in months:
        logger.debug('Processing month: %s', month)
        new_logs = []
        print('#4', time() - start)
        # find out if there are any old offending logs and remove them
        del_candidates = {}
        for rec in AccessLog.objects.\
                filter(report_type=interest_rt, platform=platform, date=month).\
                values(*(key_keys + ['pk'])):
            key = (rec[key] for key in key_keys)
            del_candidates[key] = rec['pk']
        print('#5', time() - start)
        pks_to_delete = []
        for new_log_dict in candidates.filter(metric_id__in=interest_metrics, date=month).\
                values('organization_id', 'metric_id', 'platform_id', 'target_id', 'date').\
                annotate(value=Sum('value')).iterator():
            # deal with stuff related to the metric
            metric_id = new_log_dict['metric_id']
            # fill in dim1 based on the interest group of the metric
            new_log_dict['dim1'] = metric_to_dim1[metric_id]
            # remap metric to target metric if desired
            new_log_dict['metric_id'] = metric_remap.get(metric_id, metric_id)
            new_logs.append(new_log_dict)
            # have a look if we need to delete some previous record
            key = (new_log_dict[key] for key in key_keys)
            del_pk = del_candidates.get(key)
            if del_pk:
                pks_to_delete.append(del_pk)
        print('#6', time() - start)
        AccessLog.objects.filter(pk__in=pks_to_delete).delete()
        # finally create the new access logs
        print('#7', time() - start)
        ib = ImportBatch.objects.create(report_type=interest_rt, platform=platform)
        AccessLog.objects.bulk_create(
            AccessLog(report_type=interest_rt, import_batch=ib, **new_log) for new_log in new_logs)
        print('#8', time() - start)
        stats['new_logs'] += len(new_logs)
        stats['removed_logs'] += len(pks_to_delete)
        logger.debug('Stats sofar: %s', stats)
    return stats
