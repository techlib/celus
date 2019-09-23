"""
Celery tasks related to SUSHI fetching
"""
import celery

from core.task_support import cache_based_lock
from .logic.fetching import retry_queued, fetch_new_sushi_data
from sushi.models import SushiFetchAttempt


@celery.task
def run_sushi_fetch_attempt_task(attempt_id: int):
    attempt = SushiFetchAttempt.objects.get(pk=attempt_id)
    attempt.credentials.fetch_report(
        counter_report=attempt.counter_report,
        start_date=attempt.start_date,
        end_date=attempt.end_date,
        fetch_attempt=attempt
    )


@celery.task
def retry_queued_attempts_task():
    """
    Retry downloading data for attempts that were queued
    """
    with cache_based_lock('retry_queued_attempts_task', blocking_timeout=10):
        retry_queued(sleep_interval=5)


@celery.task
def fetch_new_sushi_data_task():
    """
    Fetch sushi data for dates and platforms where they are not available
    """
    with cache_based_lock('fetch_new_sushi_data_task', blocking_timeout=10):
        fetch_new_sushi_data()