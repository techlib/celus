import logging
from datetime import datetime, timedelta

import celery
from core.logic.error_reporting import email_if_fails
from django.conf import settings
from django.utils import timezone

from .models import Automatic, FetchIntention, RunResponse, Scheduler

logger = logging.getLogger(__name__)


BUSY_TIMEOUT = 5.0  # in seconds


@celery.shared_task
@email_if_fails
def plan_schedulers_triggering():
    """This job should be run in cron mode with high frequency."""
    logger.info("Trying to unlock schedulers which are stucked.")
    Scheduler.unlock_stucked_schedulers()
    logger.info("Planning schedulers triggering")
    for scheduler in FetchIntention.objects.schedulers_to_trigger():
        trigger_scheduler.delay(scheduler.url, False)
    logger.info("Schedulers triggering was planned")


@celery.shared_task(bind=True, time_limit=Scheduler.JOB_TIME_LIMIT)
@email_if_fails
def trigger_scheduler(self, url: str, finish: bool = False):
    """finish - tries to process entire scheduler queue"""
    logger.info("Running scheduler for url %s (finish=%s)", url, finish)
    # Get or create scheduler
    (scheduler, created) = Scheduler.objects.get_or_create(url=url)
    if created:
        logger.info("Creating scheduler with url %s", url)

    res = scheduler.run_next(self.request.id)
    logger.debug("Sheduler returned %s", res)
    if res == RunResponse.COOLDOWN or (finish and res != RunResponse.IDLE):
        # replan if in cooldown
        # or when finish is set and there are still tasks to perform
        logger.info("Scheduler with url %s replaned for later.", url)
        eta: datetime
        if res == RunResponse.BUSY:
            # Add extra timeout when scheduler is BUSY
            # so it don't gets retriggered to often
            eta = timezone.now() + timedelta(seconds=BUSY_TIMEOUT)
        else:
            eta = scheduler.when_ready

        trigger_scheduler.apply_async((url, finish), eta=eta)
    else:
        # if scheduler is busy or idle or we don't need to finish the scheduler
        # we don't need to plan new task
        logger.info("Triggering scheduler with url %s terminated.", url)


@celery.shared_task
@email_if_fails
def update_automatic_harvesting():
    if settings.AUTOMATIC_HARVESTING_ENABLED:
        logger.info("Updating planning of automatic harvesting for last month")
        Automatic.update_for_last_month()
        logger.info("Automatic planning for the last month updated")
