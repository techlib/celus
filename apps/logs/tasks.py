"""
Celery tasks reside here
"""
import celery

from core.logic.error_reporting import email_if_fails
from core.task_support import cache_based_lock
from logs.logic.attempt_import import import_new_sushi_attempts
from logs.logic.materialized_interest import sync_interest_by_import_batches, \
    recompute_interest_by_batch, smart_interest_sync


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

