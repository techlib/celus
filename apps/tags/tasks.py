import logging

import celery
from django.db import DatabaseError
from django.db.transaction import atomic

from core.logic.error_reporting import email_if_fails
from tags.models import TaggingBatch, TaggingBatchState

logger = logging.getLogger(__name__)


@celery.shared_task
@email_if_fails
@atomic
def tagging_batch_preflight_task(batch_id: int, domain_name: str = '/'):
    try:
        tb = TaggingBatch.objects.select_for_update(nowait=True).get(pk=batch_id)
        if tb.state == TaggingBatchState.INITIAL:
            tb.do_preflight(title_id_formatter=lambda title_id: f'{domain_name}titles/{title_id}')
        else:
            logger.error(f"Can't generate preflight for batch #%d (state=%s)", tb.pk, tb.state)
    except TaggingBatch.DoesNotExist:
        logger.warning("batch #%d was not found", batch_id)
    except DatabaseError as e:
        logger.warning("batch #%d is already being processed. (%s)", batch_id, e)


@celery.shared_task
@email_if_fails
@atomic
def tagging_batch_assign_tag_task(batch_id: int, domain_name: str = '/'):
    try:
        tb = TaggingBatch.objects.select_for_update(nowait=True).get(pk=batch_id)
        if tb.state == TaggingBatchState.IMPORTING:
            tb.assign_tag(title_id_formatter=lambda title_id: f'{domain_name}titles/{title_id}')
        else:
            logger.error(f"Can't process batch #%d (state=%s)", tb.pk, tb.state)
    except TaggingBatch.DoesNotExist:
        logger.warning("batch #%d was not found", batch_id)
    except DatabaseError as e:
        logger.warning("batch #%d is already being processed. (%s)", batch_id, e)


@celery.shared_task
@email_if_fails
@atomic
def tagging_batch_unassign_task(batch_id: int):
    try:
        tb = TaggingBatch.objects.select_for_update(nowait=True).get(pk=batch_id)
        if tb.state == TaggingBatchState.UNDOING:
            tb.unassign_tag()
            # set it to initial state to allow preflight to be generated again
            tb.state = TaggingBatchState.INITIAL
            tb.save()
            tagging_batch_preflight_task.apply_async(args=[batch_id], countdown=2)
        else:
            logger.error(f"Can't process batch #%d (state=%s)", tb.pk, tb.state)
    except TaggingBatch.DoesNotExist:
        logger.warning("batch #%d was not found", batch_id)
    except DatabaseError as e:
        logger.warning("batch #%d is already being processed. (%s)", batch_id, e)
