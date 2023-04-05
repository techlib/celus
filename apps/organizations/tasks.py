import celery
from core.context_managers import logged_task
from core.logic.error_reporting import email_if_fails
from organizations.logic.sync import erms_sync_organizations


@celery.shared_task
@logged_task
@email_if_fails
def erms_sync_organizations_task():
    erms_sync_organizations()
