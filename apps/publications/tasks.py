"""
Celery tasks
"""
import celery

from core.logic.error_reporting import email_if_fails
from publications.logic.sync import erms_sync_platforms


@celery.shared_task
@email_if_fails
def erms_sync_platforms_task():
    erms_sync_platforms()
