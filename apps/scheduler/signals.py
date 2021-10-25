from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from core.logic.dates import month_end, this_month
from sushi.models import SushiCredentials, CounterReportsToCredentials

from .models import Automatic, FetchIntention, FetchIntentionQueue


def _update_cr2c(automatic: Automatic, cr2c: CounterReportsToCredentials):
    if cr2c.credentials.enabled and cr2c.broken is None and cr2c.credentials.broken is None:
        # add intention
        FetchIntention.objects.get_or_create(
            not_before=Automatic.trigger_time(automatic.month),
            harvest=automatic.harvest,
            start_date=automatic.month,
            end_date=automatic.month_end,
            credentials=cr2c.credentials,
            counter_report=cr2c.counter_report,
        )
    else:
        # delete otherwise
        FetchIntention.objects.filter(
            harvest=automatic.harvest,
            start_date=automatic.month,
            end_date=automatic.month_end,
            credentials=cr2c.credentials,
            counter_report=cr2c.counter_report,
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
            automatic = Automatic.get_or_create(this_month(), instance.organization)
            if instance.enabled and not instance.broken:
                # Make sure that Automatic harvest is planned
                for cr2c in instance.counterreportstocredentials_set.all():
                    _update_cr2c(automatic, cr2c)

            else:
                # Remove from Automatic harvest
                automatic.harvest.intentions.filter(credentials=instance).delete()


@receiver(post_save, sender=CounterReportsToCredentials)
def update_intentions_from_cr2c_post_save(
    sender, instance, created, raw, using, update_fields, **kwargs
):

    # skip when automatic scheduling disabled
    if not settings.AUTOMATIC_HARVESTING_ENABLED:
        return

    with transaction.atomic():
        automatic = Automatic.get_or_create(
            month=this_month(), organization=instance.credentials.organization
        )
        _update_cr2c(automatic, instance)


@receiver(post_delete, sender=CounterReportsToCredentials)
def update_intentions_from_cr2c_post_delete(sender, instance, using, **kwargs):

    # skip when automatic scheduling disabled
    if not settings.AUTOMATIC_HARVESTING_ENABLED:
        return

    with transaction.atomic():
        start_date = this_month()
        end_date = month_end(start_date)
        FetchIntention.objects.filter(
            harvest__automatic__isnull=False,
            start_date=start_date,
            end_date=end_date,
            when_processed__isnull=True,
            credentials=instance.credentials,
            counter_report=instance.counter_report,
        ).delete(),


@receiver(post_save, sender=FetchIntention)
def fill_in_queue(sender, instance, created, raw, using, update_fields, **kwargs):
    if not instance.queue:
        queue = FetchIntentionQueue.objects.create(id=instance.pk, start=instance, end=instance)
        FetchIntention.objects.filter(pk=instance.pk).update(queue=queue)
