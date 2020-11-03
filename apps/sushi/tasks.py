"""
Celery tasks related to SUSHI fetching
"""

import logging
import typing

from collections import Counter
from datetime import datetime
from functools import wraps

import celery
from django.conf import settings

from core.logic.dates import month_end
from core.logic.error_reporting import email_if_fails
from core.task_support import cache_based_lock
from logs.tasks import (
    import_one_sushi_attempt_task,
    smart_interest_sync_task,
    sync_materialized_reports_task,
)
from scheduler.models import FetchIntention, Harvest
from sushi.models import (
    SushiFetchAttempt,
    SushiCredentials,
    CounterReportType,
    CounterReportsToCredentials,
)
from .logic.fetching import retry_queued, fetch_new_sushi_data, find_holes_in_data

logger = logging.getLogger(__name__)


def new_harvest_check(function: typing.Callable) -> typing.Callable:
    @wraps(function)
    def inner(*args, **kwargs):
        if settings.AUTOMATIC_HARVESTING_ENABLED:
            logger.warning("Fetching should be triggered only within scheduler app -> skipping")
            return
        else:
            return function(*args, **kwargs)

    return inner


@celery.shared_task
@email_if_fails
@new_harvest_check
def run_sushi_fetch_attempt_task(attempt_id: int, import_data: bool = False):
    try:
        attempt = SushiFetchAttempt.objects.get(pk=attempt_id)
    except SushiFetchAttempt.DoesNotExist:
        logger.warning("Sushi attempt '%s' was not found.", attempt_id)
        # sushi attempt was deleted in the meantime
        # e.g. someone could remove credentials
        return

    if attempt.credentials.broken is not None:
        logger.warning("Sushi attempt '%s' has broken credentials; aborting.", attempt_id)
        return

    if CounterReportsToCredentials.objects.filter(
        credentials=attempt.credentials, counter_report=attempt.counter_report, broken__isnull=False
    ).exists():
        logger.warning(
            "Sushi attempt '%s' has broken report type for credentials; aborting.", attempt_id
        )
        return

    attempt.credentials.fetch_report(
        counter_report=attempt.counter_report,
        start_date=attempt.start_date,
        end_date=attempt.end_date,
        fetch_attempt=attempt,
    )
    if import_data and attempt.can_import_data:
        import_one_sushi_attempt_task.delay(attempt.id)
        # TODO: the following is here to make onboarding more user friendly, but is probably
        # not what we want in a production environment - let's remove it one day
        smart_interest_sync_task.apply_async(countdown=3)
        sync_materialized_reports_task.apply_async(countdown=5)


@celery.shared_task
@email_if_fails
@new_harvest_check
def retry_queued_attempts_task():
    """
    Retry downloading data for attempts that were queued
    """
    with cache_based_lock('retry_queued_attempts_task', blocking_timeout=10):
        retry_queued(sleep_interval=5)


@celery.shared_task
@email_if_fails
@new_harvest_check
def fetch_new_sushi_data_task():
    """
    Fetch sushi data for dates and platforms where they are not available
    """
    with cache_based_lock('fetch_new_sushi_data_task', blocking_timeout=10):
        fetch_new_sushi_data()


@celery.shared_task
@email_if_fails
@new_harvest_check
def fetch_new_sushi_data_for_credentials_task(credentials_id: int):
    """
    Fetch sushi data for dates and platforms where they are not available - only for specific
    credentials identified by database pk
    """
    credentials = SushiCredentials.objects.get(pk=credentials_id)
    with cache_based_lock(f'fetch_new_sushi_data_task_{credentials_id}', blocking_timeout=10):
        fetch_new_sushi_data(credentials=credentials)


@celery.shared_task
@email_if_fails
def make_fetch_attempt_task(
    credentials_id: int, counter_report_id: int, start_date: datetime, end_date: datetime
):
    """
    The input data are enough to specify one SushiFetchAttempt. Create it and download the
    data.
    """
    credentials = SushiCredentials.objects.get(pk=credentials_id)
    # We check that the request can be made based on data from the credentials,
    # because the task runs independent of other tasks for the same credentials, and it is possible
    # that some other task already exhausted the daily limit for downloads or something like
    # this.
    delay = credentials.when_can_access()
    if delay:
        logger.warning('Cannot start fetch attempt for another %d s; aborting', delay)
        return

    if credentials.broken is not None:
        logger.warning('Cannot start fetch attempt for broken credentails; aborting')
        return

    counter_report = CounterReportType.objects.get(pk=counter_report_id)
    if CounterReportsToCredentials.objects.filter(
        credentials=credentials, counter_report=counter_report, broken__isnull=False
    ).exists():
        logger.warning("Cannot start fetch attempt for credentials; aborting.")
        return

    credentials.fetch_report(counter_report, start_date, end_date, use_url_lock=True)


@celery.shared_task
@email_if_fails
def retry_holes_with_new_credentials_task():
    if settings.AUTOMATIC_HARVESTING_ENABLED:
        retry_holes_with_new_credentials_task_new()
    else:
        retry_holes_with_new_credentials_task_old()


def retry_holes_with_new_credentials_task_new():
    stats = Counter()

    holes = find_holes_in_data()
    if len(holes) == 0:
        logger.debug('No holes found; aborting')
        return  # No holes
    logger.debug('Found %d holes to retry', len(holes))

    intentions: typing.List[FetchIntention] = []
    for hole in holes:

        # skip broken
        if hole.credentials.broken:
            logger.debug("Broken credentials (pk=%s); skipping", hole.credentials.pk)
            stats["broken"] += 1
            continue

        if CounterReportsToCredentials.objects.filter(
            credentials=hole.credentials, counter_report=hole.counter_report, broken__isnull=False
        ).exists():
            logger.debug(
                "Counter report (code=%s) for credentials (pk=%s) is broken; skipping",
                hole.counter_report.code,
                hole.credentials.pk,
            )
            stats["broken"] += 1
            continue

        # Missing mapping
        if not CounterReportsToCredentials.objects.filter(
            credentials=hole.credentials, counter_report=hole.counter_report, broken__isnull=True
        ).exists():
            logger.debug(
                "Counter report (code=%s) for credentials (pk=%s) is missing; skipping",
                hole.counter_report.code,
                hole.credentials.pk,
            )
            stats["missing"] += 1
            continue

        logger.debug('Trying to fill hole: %s / %s', hole.credentials, hole.date)
        intentions.append(
            FetchIntention(
                credentials=hole.credentials,
                counter_report=hole.counter_report,
                start_date=hole.date.isoformat(),
                end_date=month_end(hole.date).isoformat(),
            )
        )
        stats["planned"] += 1

    # plan harvest for missing holes
    # probably we can keep Normal priority here
    # we don't need to trigger downloads right away
    Harvest.plan_harvesting(intentions)

    logger.debug('Hole filling stats: %s', stats)


def retry_holes_with_new_credentials_task_old():
    """
    Finds holes in data using `find_holes_in_data` and runs redownload tasks for them.
    """
    holes = find_holes_in_data()
    logger.debug('Found %d holes to retry', len(holes))
    stats = Counter()
    for hole in holes:
        cred_based_delay = hole.credentials.when_can_access()
        if not hole.attempt_with_current_credentials:
            # this is what we want to process - cases when sushi credentials were updated
            if cred_based_delay == 0:
                # we are ready to retry
                logger.debug('Trying to fill hole: %s / %s', hole.credentials, hole.date)
                # we use isoformat below to make sure the date is properly serialized
                # when passed on by celery
                make_fetch_attempt_task.apply_async(
                    [],
                    dict(
                        credentials_id=hole.credentials.pk,
                        counter_report_id=hole.counter_report.pk,
                        start_date=hole.date.isoformat(),
                        end_date=month_end(hole.date).isoformat(),
                    ),
                    priority=9,
                )
                stats['started'] += 1
            else:
                logger.debug('Too soon to retry - need %d s', cred_based_delay)
                stats['too soon'] += 1
    logger.debug('Hole filling stats: %s', stats)
