import logging

import celery
from core.logic.error_reporting import email_if_fails
from django.core.mail import mail_admins
from django.utils.timezone import now

from .logic.sync import sync_identities_with_erms, sync_users_with_erms
from .models import DataSource
from .task_support import cache_based_lock

logger = logging.getLogger(__name__)


@celery.shared_task
@email_if_fails
def erms_sync_users_and_identities_task():
    with cache_based_lock('erms_sync_users_and_identities_task'):
        data_source, _created = DataSource.objects.get_or_create(
            short_name='ERMS', type=DataSource.TYPE_API
        )
        stats = sync_users_with_erms(data_source)
        logger.info('User import stats: %s', stats)
        stats = sync_identities_with_erms(data_source)
        logger.info('Identity import stats: %s', stats)


@celery.shared_task
def async_mail_admins(subject, body):
    mail_admins(subject, body)


@celery.shared_task
@email_if_fails
def fail_intentionally_task():
    raise Exception('test error')


@celery.shared_task
def empty_task_export():
    """
    Empty task to be used in the export queue to make sure that Celerus has something
    to detect stuck Celery workers by
    """
    logger.info(f"Still alive at {now()}")
