"""
Celery tasks reside here
"""
import celery
import logging

from django.db import DatabaseError
from django.db.transaction import atomic

from core.logic.error_reporting import email_if_fails
from core.task_support import cache_based_lock
from logs.logic.attempt_import import import_one_sushi_attempt, check_importable_attempt
from logs.logic.export import CSVExport
from logs.logic.materialized_interest import (
    sync_interest_by_import_batches,
    recompute_interest_by_batch,
    smart_interest_sync,
)
from logs.logic.materialized_reports import (
    sync_materialized_reports,
    update_report_approx_record_count,
)
from sushi.models import SushiFetchAttempt


logger = logging.getLogger(__file__)


@celery.shared_task
@email_if_fails
def sync_interest_task():
    """
    Synchronizes computed interest for import batches that were not processed yet
    """
    with cache_based_lock('sync_interest_task', blocking_timeout=10):
        sync_interest_by_import_batches()


@celery.shared_task
@email_if_fails
@atomic
def import_new_sushi_attempts_task():
    """
    Go over new sushi attempts that contain data and import them
    """
    try:
        # select_for_update locks fetch attempts
        attempts = SushiFetchAttempt.objects.select_for_update(nowait=True).filter(
            is_processed=False, download_success=True, contains_data=True, import_crashed=False
        )
        count = attempts.count()
        logger.info('Found %d unprocessed successful download attempts matching criteria', count)

        for i, attempt in enumerate(attempts):
            logger.info('----- Importing attempt #%d -----', i)
            try:
                import_one_sushi_attempt(attempt)
            except Exception as e:
                # we catch any kind of error to make sure that the loop does not die
                logger.error('Importing sushi attempt #%d crashed: %s', attempt.pk, e)
                attempt.mark_crashed(e)

    except DatabaseError:
        logger.warning("Sushi import attempts are currently being processed.")


@celery.shared_task
@email_if_fails
@atomic
def import_one_sushi_attempt_task(attempt_id: int, reimport: bool = False):
    """
    Tries to import a single sushi attempt task

    :attempt_id: pk of attempt to import
    :reimport: removes data and marks attempt as unprocessed before import
    """
    try:
        # select_for_update lock only a single fetch attempts
        attempt = SushiFetchAttempt.objects.select_for_update(nowait=True).get(pk=attempt_id)
        if reimport:
            attempt.unprocess()

    except SushiFetchAttempt.DoesNotExist:
        # sushi attempt was deleted in the meantime
        # e.g. someone could remove credentials
        logger.warning("Sushi attempt '%s' was not found.", attempt_id)
        return
    except DatabaseError:
        logger.warning("Sushi attempt '%s' is being processed somewhere else.", attempt_id)
        return
    try:
        check_importable_attempt(attempt)
    except ValueError as e:
        logger.warning("Sushi attempt '%d' can't be imported: %s", attempt_id, str(e))
        return
    try:
        import_one_sushi_attempt(attempt)
    except Exception as e:
        # we catch any kind of error to make sure that there is no crash
        logger.error('Importing sushi attempt #%d crashed: %s', attempt.pk, e)
        attempt.mark_crashed(e)


@celery.shared_task
@email_if_fails
def recompute_interest_by_batch_task(queryset=None):
    """
    Run recompute_interest_by_batch to reconstruct interest for all batches.
    Useful when interest definitions change.
    """
    recompute_interest_by_batch(queryset=queryset)


@celery.shared_task
@email_if_fails
def smart_interest_sync_task():
    """
    Starts the `smart_interest_sync` function to synchronize all import batches that are
    not processed or out of sync
    """
    smart_interest_sync()


@celery.shared_task
@email_if_fails
def export_raw_data_task(query_params, filename_base, zip_compress=False):
    """
    Exports raw data into a file in the MEDIA directory
    """
    exporter = CSVExport(query_params, zip_compress=zip_compress, filename_base=filename_base)
    try:
        exporter.export_raw_accesslogs_to_file()
    except Exception as e:
        exporter.store_error()
        raise e


@celery.shared_task
@email_if_fails
def sync_materialized_reports_task():
    """
    Synchronizes materialized reports for import batches that were not processed yet
    """
    with cache_based_lock('sync_materialized_reports_task', blocking_timeout=10):
        sync_materialized_reports()


@celery.shared_task
@email_if_fails
def update_report_approx_record_count_task():
    """
    Synchronizes the `approx_record_count` values for all report types
    """
    with cache_based_lock('update_report_approx_record_count_task', blocking_timeout=10):
        update_report_approx_record_count()
