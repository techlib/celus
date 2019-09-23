import celery

from organizations.logic.sync import erms_sync_organizations


@celery.task
def erms_sync_organizations_task():
    erms_sync_organizations()
