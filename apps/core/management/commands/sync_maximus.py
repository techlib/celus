from django.core.management.base import BaseCommand

from core.logic.maximus_sync import sync


class Command(BaseCommand):
    help = 'Sync to celus-maximus'

    def handle(self, *args, **options):
        sync()
