"""
Celery tasks
"""
import celery

from publications.logic.sync import erms_sync_platforms


@celery.shared_task
def erms_sync_platforms_task():
    erms_sync_platforms()
