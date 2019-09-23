"""
Celery tasks reside here
"""
import celery

from core.task_support import cache_based_lock
from logs.logic.attempt_import import import_new_sushi_attempts
from logs.logic.materialized_interest import sync_interest_by_import_batches, \
    recompute_interest_by_batch


@celery.task
def sync_interest_task():
    """
    Synchronizes computed interest for import batches that were not processed yet
    """
    with cache_based_lock('sync_interest_task'):
        sync_interest_by_import_batches()


@celery.task
def import_new_sushi_attempts_task():
    """
    Go over new sushi attempts that contain data and import them
    """
    with cache_based_lock('import_new_sushi_attempts_task'):
        import_new_sushi_attempts()


@celery.task
def recompute_interest_by_batch_task(queryset=None):
    """
    Run recompute_interest_by_batch to reconstruct interest for all batches.
    Useful when interest definitions change.
    :return:
    """
    recompute_interest_by_batch(queryset=queryset)
