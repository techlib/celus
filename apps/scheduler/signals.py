from core.logic.dates import last_month, month_end
from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from sushi.models import (
    AttemptStatus,
    CounterReportsToCredentials,
    SushiCredentials,
    SushiFetchAttempt,
)

from .models import Automatic, FetchIntention, FetchIntentionQueue


def _update_cr2c(automatic: Automatic, cr2c: CounterReportsToCredentials):
    if (
        cr2c.credentials.enabled
        and cr2c.broken is None
        and cr2c.credentials.broken is None
        and cr2c.credentials.is_verified
    ):
        # add intention
        try:
            FetchIntention.objects.get_or_create(
                not_before=Automatic.trigger_time(automatic.month),
                harvest=automatic.harvest,
                start_date=automatic.month,
                end_date=automatic.month_end,
                credentials=cr2c.credentials,
                counter_report=cr2c.counter_report,
            )
        except FetchIntention.MultipleObjectsReturned:
            # we do not care about this - it means some intention exists and that is good enough
            pass
    else:
        # delete otherwise
        FetchIntention.objects.select_for_update(skip_locked=True).filter(
            harvest=automatic.harvest,
            start_date=automatic.month,
            end_date=automatic.month_end,
            credentials=cr2c.credentials,
            counter_report=cr2c.counter_report,
            when_processed__isnull=True,
        ).delete()


@receiver(post_save, sender=SushiCredentials)
def update_intentions_from_cred_post_save(
    sender, instance, created, raw, using, update_fields, **kwargs
):
    if not settings.AUTOMATIC_HARVESTING_ENABLED:
        # skip when automatic scheduling disabled
        return

    with transaction.atomic():
        if not created:
            automatic = Automatic.get_or_create(last_month(), instance.organization)
            if instance.enabled and not instance.broken and instance.is_verified:
                # Make sure that Automatic harvest is planned
                for cr2c in instance.counterreportstocredentials_set.all():
                    _update_cr2c(automatic, cr2c)

            else:
                # Remove FetchIntentions from all unprocessed automatic harvests
                FetchIntention.objects.select_for_update(skip_locked=True).filter(
                    harvest__automatic__isnull=False,
                    when_processed__isnull=True,
                    credentials=instance,
                ).delete(),


@receiver(post_save, sender=CounterReportsToCredentials)
def update_intentions_from_cr2c_post_save(
    sender, instance, created, raw, using, update_fields, **kwargs
):

    # skip when automatic scheduling disabled
    if not settings.AUTOMATIC_HARVESTING_ENABLED:
        return

    with transaction.atomic():
        automatic = Automatic.get_or_create(
            month=last_month(), organization=instance.credentials.organization
        )
        _update_cr2c(automatic, instance)


@receiver(post_delete, sender=CounterReportsToCredentials)
def update_intentions_from_cr2c_post_delete(sender, instance, using, **kwargs):

    # skip when automatic scheduling disabled
    if not settings.AUTOMATIC_HARVESTING_ENABLED:
        return

    with transaction.atomic():
        FetchIntention.objects.select_for_update(skip_locked=True).filter(
            harvest__automatic__isnull=False,
            when_processed__isnull=True,
            credentials=instance.credentials,
            counter_report=instance.counter_report,
        ).delete(),


@receiver(post_save, sender=FetchIntention)
def fill_in_queue(sender, instance, created, raw, using, update_fields, **kwargs):
    if not instance.queue:
        queue = FetchIntentionQueue.objects.create(id=instance.pk, start=instance, end=instance)
        FetchIntention.objects.filter(pk=instance.pk).update(queue=queue)


@receiver(post_save, sender=SushiFetchAttempt)
def update_verified_for_success(sender, instance, created, raw, using, update_fields, **kwargs):

    if not settings.AUTOMATIC_HARVESTING_ENABLED:
        # skip when automatic scheduling disabled
        return

    # Only when the attempt is successful
    if instance.status not in [AttemptStatus.SUCCESS, AttemptStatus.NO_DATA]:
        return

    # Only update for current credentials
    if not instance.credentials.is_verified:
        return

    try:
        cr2c = CounterReportsToCredentials.objects.get(
            credentials=instance.credentials, counter_report=instance.counter_report
        )
    except CounterReportsToCredentials.DoesNotExist:
        # Report is not set for the credentials
        return

    automatic = Automatic.get_or_create(
        month=last_month(), organization=instance.credentials.organization
    )
    _update_cr2c(automatic, cr2c)
