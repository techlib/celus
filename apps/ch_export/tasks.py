import logging
import time

import celery
from core.logic.error_reporting import email_if_fails

from ch_export.models import AccessLogExport, AccessLogExportBatch, AccessLogExportTask

logger = logging.getLogger(__name__)


@celery.shared_task
@email_if_fails
def export_to_ch_task(task_id: int):
    task = AccessLogExportTask.objects.get(pk=task_id)
    logger.info(
        "Exporting task %d to CH - %s - %s",
        task_id,
        task.batch.export.organization,
        task.report_type.short_name,
    )
    start = time.monotonic()
    task.export_to_ch()
    end = time.monotonic()
    logger.info(
        "Exported %s for %s in %.2f seconds",
        task.report_type.short_name,
        task.batch.export.organization,
        end - start,
    )


@celery.shared_task
@email_if_fails
def start_export_tasks():
    for export in AccessLogExport.objects.filter(enabled=True):
        export.create_batch(start_tasks=True)


@celery.shared_task
@email_if_fails
def start_export_for_organization(organization_id: int):
    """
    Create a new batch and start all report-type export tasks for a single organization
    (or consortium if organization_id is None).
    """
    export = AccessLogExport.objects.get(organization_id=organization_id)
    export.create_batch(start_tasks=True)


@celery.shared_task
@email_if_fails
def start_export_by_id(export_id: int):
    """
    Create a new batch and start all report-type export tasks for a specific AccessLogExport.
    """
    export = AccessLogExport.objects.get(pk=export_id)
    export.create_batch(start_tasks=True)


@celery.shared_task
@email_if_fails
def refresh_export_tags_task(export_batch_id: int):
    export_batch = AccessLogExportBatch.objects.get(pk=export_batch_id)
    start = time.monotonic()
    export_batch.refresh_export_tags()
    end = time.monotonic()
    logger.info("Refreshed tags for export batch %d in %.2f seconds", export_batch_id, end - start)
