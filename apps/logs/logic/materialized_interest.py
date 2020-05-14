"""
Stuff related to the artificial (materialized) report type 'interest' and its computation
"""
import logging
from collections import Counter
from time import time
from typing import List, Dict, Iterable, Set

from django.db.models import Sum, Count, Max, F, Q, OuterRef, Subquery, Exists, Min
from django.db.transaction import atomic
from django.utils.timezone import now

from core.task_support import cache_based_lock
from logs.models import ReportType, AccessLog, DimensionText, ImportBatch, Metric, \
    ReportInterestMetric
from publications.models import Platform

logger = logging.getLogger(__name__)


def interest_report_type():
    return ReportType.objects.get(short_name='interest')


def sync_interest_by_import_batches(queryset=None) -> Counter:
    if not queryset:
        queryset = ImportBatch.objects.all()
    stats = Counter()
    interest_rt = interest_report_type()
    # we want to make sure that the ImportBatch has some accesslogs because otherwise it might
    # be that we caught it just after creation before any AccessLogs are added to it
    queryset = queryset.filter(interest_timestamp__isnull=True).\
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
    # prepare the data
    new_log_dicts = extract_interest_from_import_batch(import_batch, interest_rt)
    # compare it with existing data
    accesslog_keys = ('organization_id', 'metric_id', 'platform_id', 'target_id', 'date')
    old_log_dicts = import_batch.accesslog_set.filter(report_type=interest_rt).\
        values('pk', *accesslog_keys)
    really_new, to_delete_pks, same = \
        fast_compare_existing_and_new_records(old_log_dicts, new_log_dicts, accesslog_keys)
    # create new, remove old
    if really_new:
        AccessLog.objects.bulk_create(
            AccessLog(report_type=interest_rt, import_batch=import_batch, **log_dict)
            for log_dict in really_new)
    if to_delete_pks:
        AccessLog.objects.filter(pk__in=to_delete_pks).delete()
    # update the import batch
    import_batch.interest_timestamp = now()
    import_batch.save()
    stats['new_logs'] = len(really_new)
    stats['existing'] = same
    stats['removed'] = len(to_delete_pks)
    logger.debug('Import took: %.2f s; Stats: %s', time()-start, stats)
    return stats


def fast_compare_existing_and_new_records(
        old_records: List[Dict], new_records: List[Dict], compared_keys: Iterable, id_key='pk') \
        -> (List[Dict], Set, int):
    """
    This code assumes that old_records have extra key `id_key` which is used to report back
    IDs of old_records that are to be removed (are not present in new_records).
    :return - List of records from new records that are new,
              set of IDs (`id_key`) of old records that are to be removed,
              number of records that are the same in old and new and do not need to be synced
    """
    old_tuple_to_pk = {tuple(old_record.get(key) for key in compared_keys): old_record.get(id_key)
                       for old_record in old_records}
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
        import_batch: ImportBatch, interest_rt: ReportType) -> List[Dict]:
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
        logger.debug('Import batch report type not in platform interest: %s - %s',
                     import_batch.report_type.short_name, import_batch.platform)
        return []
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
        # we do not use update_or_create here, because it creates one select and one update
        # even if nothing has changed
        dim_text, _created = DimensionText.objects.get_or_create(
            dimension=dim1, text=ig.short_name,
            defaults={'text_local_en': ig.name_en, 'text_local_cs': ig.name_cs})
        if dim_text.text_local_en != ig.name_en or dim_text.text_local_cs != ig.name_cs:
            dim_text.text_local_en = ig.name_en
            dim_text.text_local_cs = ig.name_cs
            dim_text.save()
        metric_to_dim1[metric_id] = dim_text.pk
    # get source data for the new logs
    new_logs = []
    # for the following dates, there are data for a superseeding report type, so we do not
    # want to created interest records for them
    clashing_dates = {}
    if import_batch.report_type.superseeded_by:
        if hasattr(import_batch, 'min_date') and hasattr(import_batch, 'max_date'):
            # check if we have an annotated queryset and do not need to compute the min-max dates
            min_date = import_batch.min_date
            max_date = import_batch.max_date
        else:
            date_range = import_batch.accesslog_set.aggregate(min_date=Min('date'),
                                                              max_date=Max('date'))
            min_date = date_range['min_date']
            max_date = date_range['max_date']
        if min_date and max_date:
            # the accesslog_set might be empty and then there is nothing that could be clashing
            clashing_dates = {
                x['date'] for x in
                import_batch.report_type.superseeded_by.accesslog_set.
                filter(platform_id=import_batch.platform_id,
                       organization_id=import_batch.organization_id,
                       date__lte=max_date,
                       date__gte=min_date).
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
    return new_logs


def remove_interest(queryset=None) -> Counter:
    if not queryset:
        queryset = ImportBatch.objects.all()
    stats = Counter()
    interest_rt = interest_report_type()
    for import_batch in queryset.filter(interest_timestamp__isnull=False):
        cur_stats = remove_interest_from_import_batch(import_batch, interest_rt)
        stats += cur_stats
        stats['import_batches'] += 1
    return stats


@atomic
def remove_interest_from_import_batch(import_batch: ImportBatch, interest_rt: ReportType) ->\
        Counter:
    deleted = import_batch.accesslog_set.filter(report_type=interest_rt).delete()
    import_batch.interest_timestamp = None
    import_batch.save()
    return Counter({'deleted_accesslogs': deleted[0]})


def recompute_interest_by_batch(queryset=None):
    with cache_based_lock('sync_interest_task', blocking_timeout=10):
        # we share the lock with sync_interest_task because the two could compete for the
        # same data
        if queryset is None:
            queryset = ImportBatch.objects.filter(interest_timestamp__isnull=False)
        # report_type.superseeded_by is needed later on, so we select it here to reduce the
        # query count
        # WARNING: the following messes up the queries when they are more complex and can
        #          lead to memory exhaustion - I leave it here as a memento against future attempts
        # queryset = queryset.select_related('report_type__superseeded_by', 'platform').\
        #     annotate(min_date=Min('accesslog__date'), max_date=Max('accesslog__date'))
        interest_rt = interest_report_type()
        total_count = queryset.count()
        logger.info('Going to recompute interest for %d batches', total_count)
        stats = Counter()
        for i, import_batch in enumerate(queryset.iterator()):
            stats += sync_interest_for_import_batch(import_batch, interest_rt)
            if i % 20 == 0:
                logger.debug('Recomputed interest for %d out of %d batches, stats: %s',
                             i, total_count, stats)
        return stats


def smart_interest_sync():
    """
    Computes or recomputes interest for all import batches that need it - either are not
    processed yet or are out of sync
    """
    logger.debug('Smart syncing interest')
    for qs in find_batches_that_need_interest_sync():
        recompute_interest_by_batch(queryset=qs)


def find_batches_that_need_interest_sync():
    """
    Generator that returns querysets for different cases where ImportBatches may be out of
    sync with their interest data
    """
    for fn in (_find_unprocessed_batches,
               _find_platform_interest_changes,
               _find_metric_interest_changes,
               _find_platform_report_type_disconnect,
               _find_potentially_superseded_import_batches):
        yield fn()
    for qs in _find_report_type_metric_disconnect():  # this is a generator itself
        yield qs


def _find_unprocessed_batches():
    """batches that do not have interest processed"""
    return ImportBatch.objects.filter(interest_timestamp__isnull=True)


def _find_platform_interest_changes():
    """
    batches where interest definition changed after interest_timestamp - platforminterest change
    """
    # we must take into account both the PlatformInterestReport object that is connected through
    # platform and the one that is connected through report_type
    return ImportBatch.objects.all().\
        annotate(last_interest_change1=Max('platform__platforminterestreport__last_modified'),
                 last_interest_change2=Max('report_type__platforminterestreport__last_modified')).\
        filter(Q(last_interest_change1__gte=F('interest_timestamp')) |
               Q(last_interest_change2__gte=F('interest_timestamp')))


def _find_metric_interest_changes():
    """
    batches where interest definition changed after interest_timestamp - interestmetric change
    """
    return ImportBatch.objects.all().\
        annotate(last_interest_change=Max('report_type__reportinterestmetric__last_modified')).\
        filter(last_interest_change__gte=F('interest_timestamp'))


def _find_platform_report_type_disconnect():
    """
    batches where the platform and report_type are not (no longer) connected by
    PlatformInterestReport, but there are some interest data anyway
    """
    interest_rt = interest_report_type()
    # platforms connected to a report_type referenced by its ID
    pir_platforms = Platform.objects.filter(
        platforminterestreport__report_type_id=OuterRef('report_type_id')).values('pk')
    # access logs from one import batch and the interest report type
    access_log_query = AccessLog.objects.\
        filter(report_type=interest_rt, import_batch=OuterRef('pk')).values('pk')
    # only batches where platform is not amongst platforms that are referenced through
    # the report_type's PlatformInterestReport
    # limit to only those that do have interest stored
    query = ImportBatch.objects.\
        exclude(platform__in=Subquery(pir_platforms)).\
        annotate(has_al=Exists(access_log_query)).\
        filter(has_al=True)
    return query


def _find_report_type_metric_disconnect():
    """
    batches where the report_type and metric are not (no longer) connected by
    ReportInterestMetric, but there are some interest data anyway
    """
    interest_rt = interest_report_type()
    access_log_metric_query = AccessLog.objects.\
        filter(report_type=interest_rt, import_batch=OuterRef('pk')).values('metric_id').\
        distinct()
    # I could not find a way how to put this into one query as combining queries (such as union,
    # difference, etc.) are not supported in subqueries by Django (as of 2.2).
    # See this bug - https://code.djangoproject.com/ticket/29338
    for report_type in ReportType.objects.exclude(pk=interest_rt.pk):
        interest_metrics = Metric.objects.\
            filter(reportinterestmetric__report_type=report_type).\
            union(Metric.objects.
                  filter(source_report_interest_metrics__report_type=report_type)).\
            values('id')
        query = ImportBatch.objects.filter(report_type=report_type).\
            annotate(has_extra_metrics=Exists(access_log_metric_query.
                                              exclude(metric_id__in=interest_metrics))).\
            filter(has_extra_metrics=True)
        yield query


def _find_superseeded_import_batches():
    """
    Find import batches that have interest computed for superseeded report_type and clashing
    data appeared with the superseeding report_type

    WARNING: This works, but is incredibly slow as it does full scan of the AccessLog table;
             DO NOT USE IT!
    """
    logger.warning('This code is slooooow - do not use it')
    superseeding_al = AccessLog.objects.\
        filter(platform=OuterRef('platform'), organization=OuterRef('organization'),
               report_type=OuterRef('report_type__superseeded_by'), date=OuterRef('date'))
    al_query = AccessLog.objects.\
        filter(report_type__superseeded_by__isnull=False). \
        annotate(has_clash=Exists(superseeding_al)).\
        filter(has_clash=True).values('import_batch').distinct()
    interest_al = AccessLog.objects.filter(import_batch=OuterRef('pk'),
                                           report_type=interest_report_type())
    query = ImportBatch.objects.filter(report_type__superseeded_by__isnull=False).\
        annotate(has_interest=Exists(interest_al)).\
        filter(has_interest=True, pk__in=al_query)
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
    superseding_ib = ImportBatch.objects.\
        filter(platform=OuterRef('platform'),
               organization=OuterRef('organization'),
               report_type=OuterRef('report_type__superseeded_by'),
               interest_timestamp__gt=OuterRef('interest_timestamp')
               )
    query = ImportBatch.objects.\
        filter(report_type__superseeded_by__isnull=False). \
        annotate(has_clash=Exists(superseding_ib)).\
        filter(has_clash=True)
    return query
