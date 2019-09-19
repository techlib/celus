"""
Celery tasks reside here
"""
import celery

from core.task_support import cache_based_lock
from logs.logic.attempt_import import import_new_sushi_attempts
from logs.logic.materialized_interest import sync_interest_by_import_batches
from sushi.logic.fetching import retry_queued


@celery.task
def sync_interest_task():
    """
    Synchronizes computed interest for import batches that were not processed yet
    """
    with cache_based_lock('sync_interest_task'):
        sync_interest_by_import_batches()


@celery.task
def retry_queued_attempts_task():
    """
    Retry downloading data for attempts that were queued
    """
    with cache_based_lock('retry_queued_attempts_task'):
        retry_queued(sleep_interval=5)


@celery.task
def import_new_sushi_attempts_task():
    """
    Go over new sushi attempts that contain data and import them
    """
    with cache_based_lock('import_new_sushi_attempts_task'):
        import_new_sushi_attempts()
