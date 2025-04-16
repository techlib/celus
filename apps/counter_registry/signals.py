from django_celus_registry.tasks import registry_changed

from .models import Platform


def update_knowledgebase(sender, **kwargs):
    Platform.objects.all().sync_knowledgebase()


registry_changed.connect(update_knowledgebase)
