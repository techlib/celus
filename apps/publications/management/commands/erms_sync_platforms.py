from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from publications.logic.sync import erms_sync_platforms


class Command(BaseCommand):

    help = 'Sync platforms between ERMS and the database'

    def add_arguments(self, parser):
        pass

    @atomic
    def handle(self, *args, **options):
        stats = erms_sync_platforms()
        self.stderr.write(self.style.WARNING(f'Import stats: {stats}'))
