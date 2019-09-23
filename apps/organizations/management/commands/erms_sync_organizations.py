import logging

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from ...logic.sync import erms_sync_organizations

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Sync organizations between ERMS and the database'

    def add_arguments(self, parser):
        pass

    @atomic
    def handle(self, *args, **options):
        stats = erms_sync_organizations()
        self.stderr.write(self.style.WARNING(f'Import stats: {stats}'))
