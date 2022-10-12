import celery
from core.logic.error_reporting import email_if_fails
from django.core.cache import cache
from django.utils import translation
from export.models import FlexibleDataExport


@celery.shared_task
@email_if_fails
def process_flexible_export_task(export_id: int):
    export = FlexibleDataExport.objects.get(pk=export_id)
    if export.status == export.NOT_STARTED:

        def monitor(now, total):
            # we use cache to communicate the intermediate results
            cache.set(export.cache_key_total, total)
            cache.set(export.cache_key_current, now)

        with translation.override(export.owner.language or 'en'):
            # set the language of the export to the one preferred by the owner
            export.create_output_file(progress_monitor=monitor)


@celery.shared_task
@email_if_fails
def delete_expired_flexible_data_exports_task():
    FlexibleDataExport.objects.annotate_obsolete().filter(obsolete=True).delete()
