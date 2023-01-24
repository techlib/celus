import itertools
import logging
import pickle

import celery
import redis
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


@celery.shared_task
@email_if_fails
def flush_request_logs_to_clickhouse():
    from django.conf import settings

    from .request_logging.clickhouse import RequestLogCube, RequestLogRecord, get_logging_backend

    r = redis.Redis(
        host=settings.REQUEST_LOGGING_REDIS_HOST,
        port=settings.REQUEST_LOGGING_REDIS_PORT,
        db=settings.REQUEST_LOGGING_REDIS_DB,
    )
    # newer versions of Redis support `lpop` with `count` argument
    # but the version we have in deployment now does not,
    # so we pop the records one by one - it is pretty fast anyway

    def popper():
        while rec := r.lpop(settings.REQUEST_LOGGING_REDIS_KEY):
            yield rec

    source = popper()
    errors = []

    while batch := list(itertools.islice(source, settings.REQUEST_LOGGING_BUFFER_SIZE)):
        logger.debug(f"Syncing {len(batch)} request logs to Clickhouse")
        backend = get_logging_backend()
        to_store = []
        for rec in batch:
            # we process the records one by one to make sure that an error in one record
            # does not prevent processing of the rest
            try:
                to_store.append(RequestLogRecord(**pickle.loads(rec)))
            except Exception as exc:
                errors.append(exc)
                logger.exception("Failed to parse request log record")
        if to_store:
            backend.store_records(RequestLogCube, to_store)
    if errors:
        async_mail_admins(
            'Errors syncing request logs to Clickhouse',
            'Errors:\n\n' + '\n'.join(str(e) for e in errors),
        )
