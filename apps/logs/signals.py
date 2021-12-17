from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.db.transaction import on_commit, atomic
from django.dispatch import receiver

from logs.logic.clickhouse import delete_import_batch_from_clickhouse
from logs.models import ImportBatch, ImportBatchSyncLog


@receiver(post_delete, sender=ImportBatch)
def import_batch_delete_sync_with_clickhouse(sender, instance: ImportBatch, using, **kwargs):
    if settings.CLICKHOUSE_SYNC_ACTIVE:
        # save the import batch id as it will be modified on the instance before `on_commit`
        # is called
        import_batch_id = instance.pk

        def delete_from_clickhouse():
            delete_import_batch_from_clickhouse(import_batch_id)

        on_commit(delete_from_clickhouse)


@receiver(post_save, sender=ImportBatch)
def import_batch_create_sync_log(sender, instance: ImportBatch, using, **kwargs):
    ImportBatchSyncLog.objects.get_or_create(
        import_batch_id=instance.pk, defaults={'state': ImportBatchSyncLog.STATE_NO_CHANGE}
    )
