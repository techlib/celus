from django.conf import settings
from django_celus_registry.tasks import registry_changed

from .models import NotificationEvent, Platform


def update_knowledgebase(sender, **kwargs):
    if settings.USE_REGISTRY_AS_KNOWLEDGEBASE:
        Platform.objects.all().sync_knowledgebase()


def link_events(sender, **kwargs):
    NotificationEvent.objects.all().sync_events()
    NotificationEvent.objects.all().assign_to_users()


registry_changed.connect(update_knowledgebase)
registry_changed.connect(link_events)
