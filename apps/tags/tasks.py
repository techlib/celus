import logging

import celery
from core.context_managers import logged_task
from core.logic.error_reporting import email_if_fails
from core.logic.util import this_celus_domain
from core.models import TaskProgress
from core.tasks import async_mail_admins
from django.db import DatabaseError
from django.db.transaction import atomic

from tags.models import TaggingBatch, TaggingBatchState

logger = logging.getLogger(__name__)


@celery.shared_task
@logged_task
@email_if_fails
@atomic
def tagging_batch_preflight_task(batch_id: int, domain_name: str = '/'):
    try:
        tb = TaggingBatch.objects.select_for_update(nowait=True).get(pk=batch_id)
        if tb.state == TaggingBatchState.PREPROCESSING:
            tp = TaskProgress(task_id=celery.current_task.request.id)
            tb.do_preflight(
                title_id_formatter=lambda title_id: f'{domain_name}titles/{title_id}',
                progress_monitor=tp.store_progress,
            )
        else:
            logger.error("Can't generate preflight for batch #%d (state=%s)", tb.pk, tb.state)
    except TaggingBatch.DoesNotExist:
        logger.warning("batch #%d was not found", batch_id)
    except DatabaseError as e:
        logger.warning("batch #%d is already being processed. (%s)", batch_id, e)


@celery.shared_task
@logged_task
@email_if_fails
@atomic
def tagging_batch_assign_tag_task(batch_id: int, domain_name: str = '/'):
    try:
        tb = TaggingBatch.objects.select_for_update(nowait=True).get(pk=batch_id)
        if tb.state == TaggingBatchState.IMPORTING:
            tp = TaskProgress(task_id=celery.current_task.request.id)
            tb.assign_tag(
                title_id_formatter=lambda title_id: f'{domain_name}titles/{title_id}',
                progress_monitor=tp.store_progress,
            )
        else:
            logger.error("Can't process batch #%d (state=%s)", tb.pk, tb.state)
    except TaggingBatch.DoesNotExist:
        logger.warning("batch #%d was not found", batch_id)
    except DatabaseError as e:
        logger.warning("batch #%d is already being processed. (%s)", batch_id, e)


@celery.shared_task
@logged_task
@email_if_fails
@atomic
def tagging_batch_unassign_task(batch_id: int):
    try:
        tb = TaggingBatch.objects.select_for_update(nowait=True).get(pk=batch_id)
        if tb.state == TaggingBatchState.UNDOING:
            tp = TaskProgress(task_id=celery.current_task.request.id)
            tb.unassign_tag(progress_monitor=tp.store_progress)
            # set it to initial state to allow preflight to be generated again
            tb.state = TaggingBatchState.PREPROCESSING
            tb.save()
            tagging_batch_preflight_task.apply_async(args=[batch_id], countdown=2)
        else:
            logger.error("Can't process batch #%d (state=%s)", tb.pk, tb.state)
    except TaggingBatch.DoesNotExist:
        logger.warning("batch #%d was not found", batch_id)
    except DatabaseError as e:
        logger.warning("batch #%d is already being processed. (%s)", batch_id, e)


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
        tb.assign_tag(
            title_id_formatter=lambda title_id: f'https://{domain_name}/titles/{title_id}',
        )
        if TaggingBatch.objects.to_reprocess().exists():
            # reschedule the task to run again to process the next batch
            reprocess_due_tagging_batches_task.delay()
