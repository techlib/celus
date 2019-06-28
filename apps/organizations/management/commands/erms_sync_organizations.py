import logging

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from ...logic.sync import sync_organizations_with_erms

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Sync organizations between ERMS and the database'

    def add_arguments(self, parser):
        pass

    @atomic
    def handle(self, *args, **options):
        stats = sync_organizations_with_erms()
        self.stderr.write(self.style.WARNING(f'Import stats: {stats}'))
