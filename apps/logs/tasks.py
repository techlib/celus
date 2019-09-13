"""
Celery tasks reside here
"""
import celery

from core.task_support import cache_based_lock
from logs.logic.materialized_interest import sync_interest_by_import_batches


@celery.task
def sync_interest_task():
    with cache_based_lock('sync_interest_task'):
        sync_interest_by_import_batches()
