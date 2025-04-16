import logging

from django.core.management.base import BaseCommand
from django_celus_registry.tasks import update_registry_models

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Synchronizes Counter Registry models with counter registry"

    def handle(self, *args, **options):
        update_registry_models()
