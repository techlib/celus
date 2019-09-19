"""
Celery tasks related to SUSHI fetching
"""
import celery

from core.task_support import cache_based_lock
from .logic.fetching import retry_queued
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
    with cache_based_lock('retry_queued_attempts_task'):
        retry_queued(sleep_interval=5)
