import logging

from django.conf import settings
from django.db import IntegrityError
from django.db.models.signals import post_delete, post_save
from django.db.transaction import on_commit
from django.dispatch import receiver

from logs.constants import ACTION_INTEREST_CHANGE
from logs.logic.clickhouse import delete_import_batch_from_clickhouse
from logs.models import (
    FlexibleReport,
    FlexibleReportUserEmail,
    ImportBatch,
    ImportBatchSyncLog,
    LastAction,
    OrganizationPlatform,
    ReportInterestMetric,
)
from logs.tasks import sync_interest_for_superseded_import_batches_task

logger = logging.getLogger(__name__)


@receiver(post_delete, sender=ImportBatch)
def import_batch_delete_sync_with_clickhouse(sender, instance: ImportBatch, using, **kwargs):
    if settings.CLICKHOUSE_SYNC_ACTIVE:
        # save the import batch id as it will be modified on the instance before `on_commit`
        # is called
        import_batch_id = instance.pk

        def delete_from_clickhouse():
            delete_import_batch_from_clickhouse(import_batch_id)

        on_commit(delete_from_clickhouse)


@receiver(post_delete, sender=ImportBatch)
def sync_interest_for_superseded_import_batches(sender, instance: ImportBatch, using, **kwargs):
    """
    Look at all superseded import batches and recompute their interest if needed.
    """
    sync_interest_for_superseded_import_batches_task.delay()


@receiver(post_save, sender=ImportBatch)
def import_batch_create_sync_log(sender, instance: ImportBatch, using, **kwargs):
    ImportBatchSyncLog.objects.get_or_create(
        import_batch_id=instance.pk, defaults={"state": ImportBatchSyncLog.STATE_NO_CHANGE}
    )


@receiver(post_save, sender=ImportBatch)
def import_batch_create_organization_platform_link(sender, instance: ImportBatch, using, **kwargs):
    if instance.organization_id and instance.platform_id:
        try:
            OrganizationPlatform.objects.get_or_create(
                organization_id=instance.organization_id, platform_id=instance.platform_id
            )
        except IntegrityError:
            # this can happen inside `get_or_create` if the organization platform link gets
            # created in another process between the `get` and the `create` parts
            # we can safely ignore this
            pass


@receiver([post_delete, post_save], sender=ReportInterestMetric)
def store_last_action_interest_change_rim(sender, instance, using, **kwargs):
    LastAction.update_action(ACTION_INTEREST_CHANGE)


@receiver(post_save, sender=FlexibleReport)
def remove_flexible_report_user_emails_without_access(sender, instance, using, **kwargs):
    # go over all related mailing objects and revalidate their access level
    # if the access level is now incompatible, remove the mailing object
    for fru in FlexibleReportUserEmail.objects.filter(flexible_report=instance).select_related(
        "user"
    ):
        if not fru.has_access():
            logger.info(
                "Removing FlexibleReportUserEmail %s because the user %s does not have access to "
                "the report %s anymore",
                fru.pk,
                fru.user.pk,
                instance.pk,
            )
            fru.delete()
