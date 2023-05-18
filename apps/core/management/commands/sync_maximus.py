from core.logic.maximus_sync import sync
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Sync to celus-maximus'

    def handle(self, *args, **options):
        sync()
