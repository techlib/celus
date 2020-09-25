from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Platform


@receiver(post_save, sender=Platform)
def create_platform_interests(sender, instance, created, raw, using, update_fields, **kwargs):
    if created:
        instance.create_default_interests()
