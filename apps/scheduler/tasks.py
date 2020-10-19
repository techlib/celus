import logging

import celery

from core.logic.error_reporting import email_if_fails

from .models import FetchIntention, Scheduler, RunResponse


logger = logging.getLogger(__name__)


@celery.shared_task
@email_if_fails
def plan_schedulers_triggering():
    for scheduler in FetchIntention.objects.schedulers_to_trigger():
        trigger_scheduler.delay(scheduler.url, False)


@celery.shared_task
@email_if_fails
def trigger_scheduler(url: str, finish: bool = False):
    """ finish - tries to process entire scheduler queue """
    # Get or create scheduler
    (scheduler, created) = Scheduler.objects.get_or_create(url=url)
    if created:
        logger.info("Creating scheduler with url %s", url)

    res = scheduler.run_next()
    if res == RunResponse.COOLDOWN or (
        res in (RunResponse.PROCESSED, RunResponse.BROKEN) and finish
    ):
        # replan if in cooldown
        # or if previous was successful and finish is set
        trigger_scheduler.apply_async((url, finish), eta=scheduler.when_ready)
    else:
        # if scheduler is busy or idle or we don't need to finish the scheduler
        # we don't need to plan new task
        pass
