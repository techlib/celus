import logging
from collections import Counter
from dataclasses import dataclass, field
from itertools import chain
from typing import Dict, List, Set

from core.context_managers import needs_clickhouse_sync
from django.db.models import F, Q, Sum
from django.db.transaction import atomic, on_commit
from django.utils.timezone import now
from hcube.api.models.aggregation import Sum as HSum

from ..cubes import AccessLogCube, ch_backend
from ..models import AccessLog, ImportBatch, ImportBatchSyncLog

logger = logging.getLogger(__name__)


@needs_clickhouse_sync
@atomic()
def sync_import_batch_with_clickhouse(import_batch: ImportBatch, batch_size=10_000) -> int:
    try:
        sync_log = ImportBatchSyncLog.objects.select_for_update().get(
            import_batch_id=import_batch.pk
        )
    except ImportBatchSyncLog.DoesNotExist:
        # the sync log was deleted before we got the lock, nothing to do anymore
        return 0
    if sync_log.state in (
        ImportBatchSyncLog.STATE_NO_CHANGE,
        ImportBatchSyncLog.STATE_SYNC,
        ImportBatchSyncLog.STATE_SYNC_INTEREST,
    ):
        # all these states can be handled by simply syncing all the import batch data
        out = 0
        try:
            out = AccessLogCube.sync_import_batch_with_cube(
                ch_backend, import_batch, batch_size=batch_size
            )
        except Exception as exc:
            # we need to keep the exception in a different variable as exc will get out of scope
            # for the on_commit error function
            e = exc
            sync_log.state = ImportBatchSyncLog.STATE_SYNC
            sync_log.save()

            def error():
                raise e

            on_commit(error)
        else:
            sync_log.state = ImportBatchSyncLog.STATE_NO_CHANGE
            sync_log.save()
            # the following way of updating the date does not trigger update of last_updated
            # which is important because otherwise it would be always later than `last_clickhoused`
            # which would interfere with the way we find out-of-sync import batches
            ImportBatch.objects.filter(pk=import_batch.pk).update(last_clickhoused=now())
        return out
    elif sync_log.state == ImportBatchSyncLog.STATE_DELETE:
        # the import batch was already deleted, so we cannot do anything and just leave it
        # to be picked up by celery cleanup task
        return 0
    else:
        raise ValueError(f'Unhandled state {sync_log.state}')


@needs_clickhouse_sync
@atomic()
def sync_import_batch_interest_with_clickhouse(import_batch: ImportBatch, batch_size=10_000) -> int:
    try:
        sync_log = ImportBatchSyncLog.objects.select_for_update().get(
            import_batch_id=import_batch.pk
        )
    except ImportBatchSyncLog.DoesNotExist:
        # the sync log was deleted before we got the lock, nothing to do anymore
        return 0
    if sync_log.state == ImportBatchSyncLog.STATE_SYNC:
        # sync was not done yet - we can do that and it will sync the interest as well
        return sync_import_batch_with_clickhouse(import_batch, batch_size=batch_size)
    elif sync_log.state in (
        ImportBatchSyncLog.STATE_NO_CHANGE,
        ImportBatchSyncLog.STATE_SYNC_INTEREST,
    ):
        # the import has data synced, but no interest, we can process it as usual
        out = 0
        try:
            out = AccessLogCube.sync_import_batch_interest_with_cube(
                ch_backend, import_batch, batch_size=batch_size
            )
        except Exception as exc:
            # we need to keep the exception in a different variable as exc will get out of scope
            # for the on_commit error function
            e = exc
            sync_log.state = ImportBatchSyncLog.STATE_SYNC_INTEREST
            sync_log.save()

            def error():
                raise e

            on_commit(error)
        else:
            sync_log.state = ImportBatchSyncLog.STATE_NO_CHANGE
            sync_log.save()
        return out
    elif sync_log.state == ImportBatchSyncLog.STATE_DELETE:
        # the import batch should be deleted, let's get out of here, we do not need to sync
        return 0
    else:
        raise ValueError(f'Unhandled state {sync_log.state}')


@needs_clickhouse_sync
def sync_accesslogs_with_clickhouse_superfast(batch_size=100_000, ignore_timestamps=False) -> int:
    """
    Does sync by large batches of accesslogs which are sorted by import batch, but accesslogs
    for one import batch may be split into more 'sync batches'.

    Has longer start because it requests the accesslogs sorted by import batch, but then is
    very fast as it does not have to make a query for each import batch.
    """
    total = 0
    to_write = []
    import_batch_ids = set()
    qs = ImportBatch.objects.all()
    if not ignore_timestamps:
        qs = qs.filter(Q(last_clickhoused__isnull=True) | Q(last_clickhoused__lt=F('last_updated')))
    for al in (
        AccessLog.objects.filter(
            report_type__materialization_spec__isnull=True, import_batch__in=qs
        )
        .order_by('import_batch_id')
        .values()
        .iterator()
    ):
        to_write.append(AccessLogCube.translate_accesslog_dict_to_cube(al))
        import_batch_ids.add(al['import_batch_id'])
        if len(to_write) >= batch_size:
            ch_backend.store_records(AccessLogCube, to_write)
            total += len(to_write)
            to_write = []
            updated = ImportBatch.objects.filter(pk__in=import_batch_ids).update(
                last_clickhoused=now()
            )
            logger.debug('Synced with ClickHouse: %d records, %d import batches', total, updated)
            import_batch_ids = set()
    if to_write:
        ch_backend.store_records(AccessLogCube, to_write)
        ImportBatch.objects.filter(pk__in=import_batch_ids).update(last_clickhoused=now())
    return total + len(to_write)


@needs_clickhouse_sync
@atomic()
def delete_import_batch_from_clickhouse(import_batch_id: int):
    try:
        sync_log = ImportBatchSyncLog.objects.select_for_update().get(
            import_batch_id=import_batch_id
        )
    except ImportBatchSyncLog.DoesNotExist:
        # the sync log was deleted before we got the lock, nothing to do anymore
        return
    # in delete, we do not care about the state of the ImportBatchSyncLog as at this point
    # the ImportBatch has been deleted from postgres and the only thing we can do is to perform
    # the removal of data in clickhouse as well
    try:
        AccessLogCube.delete_import_batch(ch_backend, import_batch_id)
    except Exception as exc:
        # we need to keep the exception in a different variable as exc will get out of scope
        # for the on_commit error function
        e = exc
        sync_log.state = ImportBatchSyncLog.STATE_DELETE
        sync_log.save()

        def error():
            raise e

        on_commit(error)
    else:
        # delete the sync log - it is not of any use anymore
        sync_log.delete()


@needs_clickhouse_sync
@atomic()
def resync_import_batch_with_clickhouse(import_batch: ImportBatch):
    """
    To be used after the content of an import batch has changed in the database, and it needs
    to be re-synced with clickhouse.
    This involves deleting the whole import batch from CH and resyncing it, so use it sparingly
    """
    try:
        sync_log = ImportBatchSyncLog.objects.select_for_update().get(
            import_batch_id=import_batch.pk
        )
    except ImportBatchSyncLog.DoesNotExist:
        # the sync log was deleted before we got the lock, nothing to do anymore
        return
    # in resync mode, we do not care about the state of the ImportBatchSyncLog
    # because this overrides everything as it does both delete and sync
    try:
        AccessLogCube.delete_import_batch(ch_backend, import_batch.pk)
    except Exception as exc:
        # we need to keep the exception in a different variable as exc will get out of scope
        # for the on_commit error function
        e = exc
        sync_log.state = ImportBatchSyncLog.STATE_RESYNC
        sync_log.save()

        def error():
            raise e

        on_commit(error)
    else:
        sync_log.state = ImportBatchSyncLog.STATE_SYNC
        sync_log.save()

        def do_sync():
            sync_import_batch_with_clickhouse(import_batch)

        on_commit(do_sync)


@needs_clickhouse_sync
def process_one_import_batch_sync_log(import_batch_id):
    try:
        # we do not .select_for_update as this is done in the functions called from here
        sync_log = ImportBatchSyncLog.objects.get(pk=import_batch_id)
    except ImportBatchSyncLog.DoesNotExist:
        # it is possible that the sync_log does not exist anymore
        return
    if sync_log.state == ImportBatchSyncLog.STATE_NO_CHANGE:
        # nothing to do - maybe the sync log was processed before we got the lock
        return
    elif sync_log.state == ImportBatchSyncLog.STATE_SYNC:
        ib = ImportBatch.objects.get(pk=sync_log.import_batch_id)
        sync_import_batch_with_clickhouse(ib)
    elif sync_log.state == ImportBatchSyncLog.STATE_SYNC_INTEREST:
        ib = ImportBatch.objects.get(pk=sync_log.import_batch_id)
        sync_import_batch_interest_with_clickhouse(ib)
    elif sync_log.state == ImportBatchSyncLog.STATE_DELETE:
        delete_import_batch_from_clickhouse(sync_log.import_batch_id)
    elif sync_log.state == ImportBatchSyncLog.STATE_RESYNC:
        ib = ImportBatch.objects.get(pk=sync_log.import_batch_id)
        resync_import_batch_with_clickhouse(ib)
    else:
        raise ValueError(f'ImportBatchSyncLog.state has unknown value "{sync_log.state}"')


@dataclass
class ComparisonResult:
    stats: Dict[str, int] = field(default_factory=Counter)
    import_batches_to_resync: Set[int] = field(default_factory=set)
    import_batches_to_delete: Set[int] = field(default_factory=set)
    log: List[str] = field(default_factory=list)

    def is_ok(self):
        return not any(key for key in self.stats.keys() if key != 'ok')


def compare_db_with_clickhouse() -> ComparisonResult:
    result = ComparisonResult()
    in_db = (
        AccessLog.objects.values('import_batch_id', 'metric_id')
        .filter(report_type__materialization_spec__isnull=True)
        .order_by('import_batch_id', 'metric_id')
        .annotate(score=Sum('value'))
        .iterator()
    )
    in_ch = ch_backend.get_records(
        AccessLogCube.query()
        .group_by('import_batch_id', 'metric_id')
        .order_by('import_batch_id', 'metric_id')
        .aggregate(score=HSum('value'))
    )

    ch_rec = next(in_ch, None)
    db_rec = next(in_db, None)
    while db_rec:
        db_ib_id = db_rec['import_batch_id']
        db_m_id = db_rec['metric_id']
        db_score = db_rec['score']
        if ch_rec and (db_ib_id, db_m_id) == (ch_rec.import_batch_id, ch_rec.metric_id):
            # we are on the same record
            if db_score != ch_rec.score:
                result.log.append(f'!! {db_ib_id}, {db_m_id}: DB: {db_score}, CH: {ch_rec.score}')
                result.stats['value mismatch'] += 1
                result.import_batches_to_resync.add(db_ib_id)
            else:
                result.stats['ok'] += 1
            ch_rec = next(in_ch, None)
            db_rec = next(in_db, None)
        elif ch_rec and (db_ib_id, db_m_id) > (ch_rec.import_batch_id, ch_rec.metric_id):
            # this record is only in CH
            while ch_rec and (db_ib_id, db_m_id) > (ch_rec.import_batch_id, ch_rec.metric_id):
                result.log.append(
                    f'CH {ch_rec.import_batch_id}, {ch_rec.metric_id}: {ch_rec.score}'
                )
                result.stats['ch extra'] += 1
                result.import_batches_to_delete.add(ch_rec.import_batch_id)
                ch_rec = next(in_ch, None)
        else:
            # this record is only in DB
            result.log.append(f'DB {db_ib_id}, {db_m_id}: {db_score}')
            result.stats['db extra'] += 1
            result.import_batches_to_resync.add(db_ib_id)
            db_rec = next(in_db, None)
    # we might have some records left in CH
    # if ch was exhausted, ch_rec should be None, if not, we have to add the rest
    all_in_ch = chain([ch_rec], in_ch) if ch_rec else in_ch
    for ch_rec in all_in_ch:
        result.log.append(f'CH {ch_rec.import_batch_id}, {ch_rec.metric_id}: {ch_rec.score}')
        result.stats['ch extra'] += 1
        result.import_batches_to_delete.add(ch_rec.import_batch_id)
    return result


@needs_clickhouse_sync
def deal_with_comparison_results(results: ComparisonResult):
    for ib in ImportBatch.objects.filter(pk__in=results.import_batches_to_resync):
        logger.debug('Resyncing #%s', ib.pk)
        resync_import_batch_with_clickhouse(ib)
    for ib_id in results.import_batches_to_delete:
        logger.debug('Deleting #%s', ib_id)
        AccessLogCube.delete_import_batch(ch_backend, ib_id)
