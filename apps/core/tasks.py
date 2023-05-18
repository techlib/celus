import itertools
import logging
import pickle
from random import randint

import celery
import redis
from celery.signals import task_postrun
from core.logic.error_reporting import email_if_fails
from django.core.cache import cache
from django.core.mail import mail_admins, send_mail
from django.utils.timezone import now

from .context_managers import logged_task
from .logic.mailchimp import SyncTask
from .logic.maximus_sync import sync as maximus_sync
from .logic.sync import sync_identities_with_erms, sync_users_with_erms
from .models import DataSource
from .request_logging.celery_capture import celery_task_log
from .task_support import cache_based_lock

logger = logging.getLogger(__name__)
task_postrun.connect(celery_task_log)


@celery.shared_task
@logged_task
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
def async_mail_mailchimp_admins(subject, body):
    from django.conf import settings

    recipients = settings.MAILCHIMP_ADMINS if settings.MAILCHIMP_ADMINS else settings.ADMINS
    send_mail(subject, body, recipient_list=recipients)


@celery.shared_task
@logged_task
@email_if_fails
def fail_intentionally_task():
    raise Exception('test error')


@celery.shared_task
@logged_task
def empty_task_export():
    """
    Empty task to be used in the export queue to make sure that Celerus has something
    to detect stuck Celery workers by
    """
    logger.info(f"Still alive at {now()}")


@celery.shared_task
@logged_task
@email_if_fails
def flush_request_logs_to_clickhouse():
    from django.conf import settings

    from .request_logging.clickhouse import (
        CeleryTaskLogCube,
        CeleryTaskLogRecord,
        RequestLogCube,
        RequestLogRecord,
        get_logging_backend,
    )

    r = redis.Redis(
        host=settings.REQUEST_LOGGING_REDIS_HOST,
        port=settings.REQUEST_LOGGING_REDIS_PORT,
        db=settings.REQUEST_LOGGING_REDIS_DB,
    )
    # newer versions of Redis support `lpop` with `count` argument
    # but the version we have in deployment now does not,
    # so we pop the records one by one - it is pretty fast anyway

    for name, key, record_cls, cube, condition in (
        (
            'request',
            settings.REQUEST_LOGGING_REDIS_KEY,
            RequestLogRecord,
            RequestLogCube,
            settings.CLICKHOUSE_REQUEST_LOGGING,
        ),
        (
            'celery',
            settings.CELERY_LOGGING_REDIS_KEY,
            CeleryTaskLogRecord,
            CeleryTaskLogCube,
            settings.CLICKHOUSE_CELERY_TASK_LOGGING,
        ),
    ):
        if not condition:
            continue

        def popper():
            while rec := r.lpop(key):
                yield rec

        source = popper()
        errors = []

        while batch := list(itertools.islice(source, settings.REQUEST_LOGGING_BUFFER_SIZE)):
            logger.debug(f"Syncing {len(batch)} {name} logs to Clickhouse")
            backend = get_logging_backend()
            to_store = []
            for rec in batch:
                # we process the records one by one to make sure that an error in one record
                # does not prevent processing of the rest
                try:
                    to_store.append(record_cls(**pickle.loads(rec)))
                except Exception as exc:
                    errors.append(exc)
                    logger.exception(f"Failed to parse {name} log record")
            if to_store:
                backend.store_records(cube, to_store)
        if errors:
            async_mail_admins(
                f'Errors syncing {name} logs to Clickhouse',
                'Errors:\n\n' + '\n'.join(str(e) for e in errors),
            )


@celery.shared_task
@logged_task
@email_if_fails
def update_prometheus_db_stats():
    from .prometheus import CACHE_STORED_GAUAGES

    for name, params in CACHE_STORED_GAUAGES.items():
        if fn := params.get('func'):
            cache.set(name, fn())


@celery.shared_task
@logged_task
@email_if_fails
def sync_mailchimp_contacts_with_celus_task():
    """
    Synchronize Mailchimp audience contacts with Celus users.
    """

    task = SyncTask()
    task.fetch_members_from_mailchimp()
    if task.members_data:
        task.parse_members_data()
        task.get_all_relevant_celususers()
        task.add_new_members()
        task.update_or_delete_members()
    email = task.create_report_email()
    if email:
        async_mail_mailchimp_admins.delay(email["subject"], email["body"])


@celery.shared_task
@logged_task
@email_if_fails
def sync_mailchimp_contacts_with_celus_delayed_task():
    """
    Schedules `sync_mailchimp_contacts_with_celus_task` to be run in the future with a random delay.
    This is used to avoid running the task at the same time on all Celus installations.
    """
    delay = randint(0, 60 * 60)
    logger.info('Scheduling `sync_mailchimp_contacts_with_celus_task` in %d seconds', delay)
    sync_mailchimp_contacts_with_celus_task.apply_async(countdown=delay)


@celery.shared_task
@logged_task
@email_if_fails
def sync_with_maximus_task():
    """
    Synchronize data with Celus-Maximus.
    """
    maximus_sync()
