import logging
from datetime import timedelta

import celery
from core.logic.error_reporting import email_if_fails
from django.db import transaction
from django.utils.timezone import now
from django_celery_results.models import TaskResult

logger = logging.getLogger(__file__)


DELAY_OFFSET = timedelta(hours=1)


@celery.shared_task
@email_if_fails
def delete_batch_targets(batch_id):
    from .models import Batch

    try:
        batch = Batch.objects.get(pk=batch_id)
    except Batch.DoesNotExist:
        logger.warning("Batch not found %d (deleted?)", batch_id)
        return

    count = batch.delete_batch_targets(
        TaskResult.objects.filter(task_id__iexact=celery.current_task.request.id).first()
    )
    if count is None:
        logger.warning("Import batch is being used %d", batch_id)
    elif count == 0:
        logger.warning("No record to delete in batch %d (already deleted?)", batch_id)
    else:
        logger.info("Batch %d data were deleted (count=%d)", batch_id, count)


@celery.shared_task
@email_if_fails
def delete_batches_targets():
    from .models import Batch, BatchStatus

    with transaction.atomic():
        for batch in (
            Batch.objects.filter(status=BatchStatus.DELETE)
            .filter(created__lt=now() - DELAY_OFFSET)
            .select_for_update(skip_locked=True)
        ):
            # plant to delete
            delete_batch_targets.delay(batch.id)


@celery.shared_task
@email_if_fails
def prepare_batch(batch_id):
    from .models import Batch

    try:
        batch = Batch.objects.get(pk=batch_id)
    except Batch.DoesNotExist:
        logger.warning("Batch not found %d (deleted?)", batch_id)
        return

    count = batch.prepare_batch(
        TaskResult.objects.filter(task_id__iexact=celery.current_task.request.id).first()
    )
    if count is None:
        logger.warning("Import batch is being used %d", batch_id)
    elif count == 0:
        logger.warning("Batch %d has no records", batch_id)
    else:
        logger.info("Batch %d info was updated (count=%d)", batch_id, count)


@celery.shared_task
@email_if_fails
def prepare_batches():
    from .models import Batch, BatchStatus

    with transaction.atomic():
        for batch in (
            Batch.objects.filter(status=BatchStatus.INITIAL)
            .filter(created__lt=now() - DELAY_OFFSET)
            .select_for_update(skip_locked=True)
        ):
            # plant to generate info
            prepare_batch.delay(batch.id)
