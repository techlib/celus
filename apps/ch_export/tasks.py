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
        batch = AccessLogExportBatch.objects.create(export=export)
        for report_type in export.report_types():
            where = {"report_type_id": report_type.pk}
            if export.organization:
                where["organization_id"] = export.organization.pk

            task = AccessLogExportTask.objects.create(batch=batch, report_type=report_type)
            celery_task = export_to_ch_task.apply_async((task.id,), countdown=2)
            task.task_id = celery_task.id
            task.save()
