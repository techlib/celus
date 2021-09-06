from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from api.models import OrganizationAPIKey

from .models import RouterSyncAttempt


@receiver(post_save, sender=OrganizationAPIKey)
def create_present_router_sync_attempt(
    sender, instance, created, raw, using, update_fields, **kwargs
):
    RouterSyncAttempt.propagate_prefix(instance.prefix, RouterSyncAttempt.Target.PRESENT)


@receiver(post_delete, sender=OrganizationAPIKey)
def create_absent_router_sync_attempt(sender, instance, using, **kwargs):
    RouterSyncAttempt.propagate_prefix(instance.prefix, RouterSyncAttempt.Target.ABSENT)
