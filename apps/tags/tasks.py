import logging
from typing import Optional

import celery
from core.context_managers import logged_task
from core.logic.error_reporting import email_if_fails
from core.logic.util import this_celus_domain
from core.models import TaskProgress
from core.tasks import async_mail_admins
from django.db import DatabaseError, transaction
from django.db.transaction import atomic
from events.models import Event, EventCategory, EventImportance

from tags.models import TaggingBatch, TaggingBatchState

logger = logging.getLogger(__name__)


def grab_tagging_batch(batch_id) -> Optional[TaggingBatch]:
    try:
        tb = TaggingBatch.objects.select_for_update(nowait=True).get(pk=batch_id)
    except TaggingBatch.DoesNotExist:
        logger.warning("batch #%d was not found", batch_id)
        return
    except DatabaseError as e:
        logger.warning("batch #%d is already being processed. (%s)", batch_id, e)
        return
    return tb


@celery.shared_task
@logged_task
@email_if_fails
@atomic
def tagging_batch_preflight_task(batch_id: int, domain_name: str = "/"):
    if not (tb := grab_tagging_batch(batch_id)):
        return

    if tb.state != TaggingBatchState.PREPROCESSING:
        logger.error("Can't generate preflight for batch #%d (state=%s)", tb.pk, tb.state)
        return

    tp = TaskProgress(task_id=celery.current_task.request.id)
    preflight = tb.do_preflight(
        title_id_formatter=lambda title_id: f"{domain_name}titles/{title_id}",
        progress_monitor=tp.store_progress,
    )
    # create corresponding event
    if preflight.success:
        title = "Pre-processing of title list has finished"
        importance = EventImportance.NORMAL
        description = (
            f"Title list #{tb.pk} {tb.context_desc} was pre-processed, "
            f"{preflight.unique_matched_titles} titles were matched.",
        )
    else:
        title = "Pre-processing of title list failed"
        importance = EventImportance.HIGH
        description = (
            f"An error occurred while pre-processing title list #{tb.pk} {tb.context_desc}:"
            f"\n\n{preflight.error}"
        )

    if users_to_notify := tb.users_to_notify():
        Event.create_for_users(
            users_to_notify,
            title=title,
            description=description,
            importance=importance,
            category=EventCategory.TAGS,
        )


@celery.shared_task
@logged_task
@email_if_fails
@atomic
def tagging_batch_assign_tag_task(batch_id: int, domain_name: str = "/"):
    if not (tb := grab_tagging_batch(batch_id)):
        return

    if tb.state != TaggingBatchState.IMPORTING:
        logger.error("Can't process batch #%d (state=%s)", tb.pk, tb.state)
        return

    tp = TaskProgress(task_id=celery.current_task.request.id)
    postflight = tb.assign_tag(
        title_id_formatter=lambda title_id: f"{domain_name}titles/{title_id}",
        progress_monitor=tp.store_progress,
    )

    if postflight.success:
        title = "Processing of title list has finished"
        importance = EventImportance.NORMAL
        description = (
            f"Title list #{tb.pk} {tb.context_desc} has been processed, {postflight.tagged_titles} "
            f"titles were tagged.",
        )
    else:
        title = "Processing of title list failed"
        importance = EventImportance.HIGH
        description = (
            f"An error occurred while processing title list #{tb.pk} {tb.context_desc}:"
            f"\n\n{postflight.error}"
        )

    if users_to_notify := tb.users_to_notify():
        Event.create_for_users(
            users_to_notify,
            title=title,
            description=description,
            importance=importance,
            category=EventCategory.TAGS,
        )


@celery.shared_task
@logged_task
@email_if_fails
@atomic
def tagging_batch_unassign_task(batch_id: int):
    if not (tb := grab_tagging_batch(batch_id)):
        return

    if tb.state != TaggingBatchState.UNDOING:
        logger.error("Can't process batch #%d (state=%s)", tb.pk, tb.state)
        return

    tp = TaskProgress(task_id=celery.current_task.request.id)
    tb.unassign_tag(progress_monitor=tp.store_progress)
    # set it to initial state to allow preflight to be generated again
    tb.state = TaggingBatchState.PREPROCESSING
    tb.save()
    tagging_batch_preflight_task.apply_async(args=[batch_id], countdown=2)


@celery.shared_task
@logged_task
@email_if_fails
@atomic
def reprocess_due_tagging_batches_task():
    """
    Re-processes the next batch that is due for processing. If more batches are due, it will
    reschedule itself to run
    """
    try:
        tb = TaggingBatch.objects.to_reprocess().select_for_update(nowait=True).first()
    except DatabaseError as e:
        async_mail_admins.delay("Can't fetch a batch to reprocess - all seem locked", str(e))
        return
    if tb:
        domain_name = this_celus_domain()
        tb.state = TaggingBatchState.IMPORTING
        tb.save()

        postflight = tb.assign_tag(
            title_id_formatter=lambda title_id: f"https://{domain_name}/titles/{title_id}"
        )

        # create corresponding event
        if postflight.success:
            title = "Periodic re-processing of title list was performed"
            importance = EventImportance.NORMAL
            description = (
                f"Title list #{tb.pk} {tb.context_desc} was re-processed, "
                f"{postflight.tagged_titles} titles were tagged."
            )
        else:
            title = "Periodic re-processing of title list failed"
            importance = EventImportance.HIGH
            description = (
                f"An error occurred while processing title list #{tb.pk} {tb.context_desc}:"
                f"\n\n{postflight.error}"
            )

        if users_to_notify := tb.users_to_notify():
            Event.create_for_users(
                users_to_notify,
                title=title,
                description=description,
                importance=importance,
                category=EventCategory.TAGS,
            )

        # reschedule the task to run again to process the next batch
        # we do it in an on_commit hook to make sure the current tb is written into DB and unlocked
        # we also add a delay to make sure the current task is finished
        if TaggingBatch.objects.to_reprocess().exists():
            transaction.on_commit(
                lambda: reprocess_due_tagging_batches_task.apply_async(countdown=1)
            )
