import itertools
import logging
import pickle
from datetime import datetime, timedelta
from time import time

import celery
import redis
from celery.signals import task_postrun
from django.core.cache import cache
from django.core.mail import mail_admins
from django.utils.timezone import now

from core.logic.error_reporting import email_if_fails

from .context_managers import logged_task
from .logic.email import mail_customer_care_admins
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
    with cache_based_lock("erms_sync_users_and_identities_task"):
        data_source, _created = DataSource.objects.get_or_create(
            short_name="ERMS", type=DataSource.TYPE_API
        )
        stats = sync_users_with_erms(data_source)
        logger.info("User import stats: %s", stats)
        stats = sync_identities_with_erms(data_source)
        logger.info("Identity import stats: %s", stats)


@celery.shared_task
def async_mail_admins(subject, body):
    mail_admins(subject, body)


@celery.shared_task
def async_mail_customer_care_admins(subject, body):
    mail_customer_care_admins(subject, body)


@celery.shared_task
@logged_task
@email_if_fails
def fail_intentionally_task():
    raise Exception("test error")


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
            "request",
            settings.REQUEST_LOGGING_REDIS_KEY,
            RequestLogRecord,
            RequestLogCube,
            settings.CLICKHOUSE_REQUEST_LOGGING,
        ),
        (
            "celery",
            settings.CELERY_LOGGING_REDIS_KEY,
            CeleryTaskLogRecord,
            CeleryTaskLogCube,
            settings.CLICKHOUSE_CELERY_TASK_LOGGING,
        ),
    ):
        if not condition:
            continue

        def popper():
            while rec := r.lpop(key):  # noqa: B023
                yield rec

        source = popper()
        errors = []
        sync_canceled = False

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
                    logger.exception("Failed to parse %s log record", name)

            if to_store:
                try:
                    backend.store_records(cube, to_store)
                    logger.debug(
                        "Successfully stored %d %s records to Clickhouse", len(to_store), name
                    )
                except Exception as exc:
                    logger.error("Failed to store %s records to Clickhouse: %s", name, exc)
                    # Put the data back into Redis for retry
                    for rec in batch:
                        r.rpush(key, rec)
                    logger.info("Restored %d %s records back to Redis for retry", len(batch), name)
                    # Cancel sync for this batch and continue with next batch
                    sync_canceled = True

            # If we've canceled sync, don't process more batches
            if sync_canceled:
                logger.warning("Sync canceled for %s logs due to Clickhouse write failure", name)
                # find the oldest record in the batch
                oldest_record = min(to_store, key=lambda x: x.timestamp)
                # if the oldest record is older than 1 hour, send an email to the admins
                if oldest_record.timestamp < datetime.now(
                    oldest_record.timestamp.tzinfo
                ) - timedelta(hours=1):
                    async_mail_admins(
                        f"Sync canceled for {name} logs due to Clickhouse write failure",
                        f"The oldest record is older than 1 hour: {oldest_record.timestamp}, which "
                        "means the problem persists and should be investigated. Celery logs should "
                        "contain information about the error.",
                    )
                break

        if errors:
            async_mail_admins(
                f"Errors syncing {name} logs to Clickhouse",
                "Errors:\n\n" + "\n".join(str(e) for e in errors),
            )


@celery.shared_task
@logged_task
@email_if_fails
def update_prometheus_db_stats():
    from .prometheus import CACHE_STORED_GAUAGES

    for name, params in CACHE_STORED_GAUAGES.items():
        if fn := params.get("func"):
            start = time()
            cache.set(name, fn(), timeout=7200)  # 2 hours, celery beat runs this every 57 minutes
            logger.info("Updated '%s' in %.2f s", name, time() - start)


@celery.shared_task
@logged_task
@email_if_fails
def sync_with_maximus_task():
    """
    Synchronize data with CELUS-Maximus.
    """
    maximus_sync()
