import logging

from datetime import timedelta

import celery
from django.conf import settings

from core.logic.error_reporting import email_if_fails

from .models import FetchIntention, Scheduler, RunResponse, Automatic


logger = logging.getLogger(__name__)


@celery.shared_task
@email_if_fails
def plan_schedulers_triggering():
    """ This job should be run in cron mode with high frequency. """
    logger.info("Planning schedulers triggering")
    for scheduler in FetchIntention.objects.schedulers_to_trigger():
        trigger_scheduler.delay(scheduler.url, False)
    logger.info("Schedulers triggering was planned")


@celery.shared_task
@email_if_fails
def trigger_scheduler(url: str, finish: bool = False):
    """ finish - tries to process entire scheduler queue """
    logger.info("Running scheduler for url %s (finish=%s)", url, finish)
    # Get or create scheduler
    (scheduler, created) = Scheduler.objects.get_or_create(url=url)
    if created:
        logger.info("Creating scheduler with url %s", url)

    res = scheduler.run_next()
    logger.debug("Sheduler returned %s", res)
    if res == RunResponse.COOLDOWN or (finish and res != RunResponse.IDLE):
        # replan if in cooldown
        # or when finish is set and there are still tasks to perform
        logger.info("Scheduler with url %s replaned for later.", url)
        timeout: timedelta
        if res == RunResponse.BUSY:
            # Add extra timeout when scheduler is BUSY
            # so it don't gets retriggered to often
            timeout = timedelta(seconds=scheduler.cooldown)
        else:
            timeout = timedelta(seconds=0)

        trigger_scheduler.apply_async((url, finish), eta=scheduler.when_ready + timeout)
    else:
        # if scheduler is busy or idle or we don't need to finish the scheduler
        # we don't need to plan new task
        logger.info("Triggering scheduler with url %s terminated.", url)


@celery.shared_task
@email_if_fails
def update_automatic_harvesting():
    if settings.AUTOMATIC_HARVESTING_ENABLED:
        logger.info("Updating planning of automatic harvesting for the next month")
        Automatic.update_for_next_month()
        logger.info("Automatic planning for the next month updated")
