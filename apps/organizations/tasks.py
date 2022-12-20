import celery
from core.logic.error_reporting import email_if_fails
from organizations.logic.sync import erms_sync_organizations


@celery.shared_task
@email_if_fails
def erms_sync_organizations_task():
    erms_sync_organizations()
