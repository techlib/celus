"""
Celery tasks related to SUSHI fetching
"""
import celery

from core.logic.error_reporting import email_if_fails
from core.task_support import cache_based_lock
from .logic.fetching import retry_queued, fetch_new_sushi_data
from sushi.models import SushiFetchAttempt, SushiCredentials


@celery.shared_task
@email_if_fails
def run_sushi_fetch_attempt_task(attempt_id: int):
    attempt = SushiFetchAttempt.objects.get(pk=attempt_id)
    attempt.credentials.fetch_report(
        counter_report=attempt.counter_report,
        start_date=attempt.start_date,
        end_date=attempt.end_date,
        fetch_attempt=attempt,
    )


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
