"""
Celery tasks related to SUSHI fetching
"""
import logging
from collections import Counter
from datetime import datetime

import celery

from core.logic.dates import month_end
from core.logic.error_reporting import email_if_fails
from core.task_support import cache_based_lock
from logs.tasks import import_one_sushi_attempt_task
from sushi.models import SushiFetchAttempt, SushiCredentials, CounterReportType
from .logic.fetching import retry_queued, fetch_new_sushi_data, find_holes_in_data

logger = logging.getLogger(__name__)


@celery.shared_task
@email_if_fails
def run_sushi_fetch_attempt_task(attempt_id: int, import_data: bool = False):
    attempt = SushiFetchAttempt.objects.get(pk=attempt_id)
    attempt.credentials.fetch_report(
        counter_report=attempt.counter_report,
        start_date=attempt.start_date,
        end_date=attempt.end_date,
        fetch_attempt=attempt,
    )
    if import_data:
        import_one_sushi_attempt_task.delay(attempt.id)


@celery.shared_task
@email_if_fails
def retry_queued_attempts_task():
    """
    Retry downloading data for attempts that were queued
    """
    with cache_based_lock('retry_queued_attempts_task', blocking_timeout=10):
        retry_queued(sleep_interval=5)


@celery.shared_task
@email_if_fails
def fetch_new_sushi_data_task():
    """
    Fetch sushi data for dates and platforms where they are not available
    """
    with cache_based_lock('fetch_new_sushi_data_task', blocking_timeout=10):
        fetch_new_sushi_data()


@celery.shared_task
@email_if_fails
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
    counter_report = CounterReportType.objects.get(pk=counter_report_id)
    credentials.fetch_report(counter_report, start_date, end_date, use_url_lock=True)


@celery.shared_task
@email_if_fails
def retry_holes_with_new_credentials_task():
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
