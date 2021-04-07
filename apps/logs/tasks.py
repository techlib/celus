"""
Celery tasks reside here
"""
import celery
import logging

from core.logic.error_reporting import email_if_fails
from core.task_support import cache_based_lock
from logs.logic.attempt_import import import_new_sushi_attempts, import_one_sushi_attempt
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
def import_new_sushi_attempts_task():
    """
    Go over new sushi attempts that contain data and import them
    """
    with cache_based_lock('import_new_sushi_attempts_task', blocking_timeout=10):
        import_new_sushi_attempts()


@celery.shared_task
@email_if_fails
def import_one_sushi_attempt_task(attempt_id: int):
    """
    Tries to import a single sushi attempt task
    """
    with cache_based_lock('import_new_sushi_attempts_task', blocking_timeout=10):
        try:
            attempt = SushiFetchAttempt.objects.get(pk=attempt_id)
        except SushiFetchAttempt.DoesNotExist:
            # sushi attempt was deleted in the meantime
            # e.g. someone could remove credentials
            logger.warning("Sushi attempt '%s' was not found.", attempt_id)
            return
        import_one_sushi_attempt(attempt)


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
