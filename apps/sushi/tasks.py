import celery
from core.context_managers import logged_task
from core.logic.error_reporting import email_if_fails

from sushi.logic.cleanup import delete_fetchattempts_and_related_importbatches


@celery.shared_task
@logged_task
@email_if_fails
def delete_fetchattempts_and_related_importbatches_task(fetch_attempts_pks: list):
    delete_fetchattempts_and_related_importbatches(fetch_attempts_pks)
