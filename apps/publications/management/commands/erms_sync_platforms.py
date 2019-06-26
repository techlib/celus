import logging

from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from django.conf import settings

from ...logic.sync import PlaformSyncer
from erms.api import ERMS

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Sync platforms between ERMS and the database'

    def add_arguments(self, parser):
        pass

    @atomic
    def handle(self, *args, **options):
        erms = ERMS(base_url=settings.ERMS_API_URL)
        erms_records = erms.fetch_objects(ERMS.CLS_PLATFORM)
        syncer = PlaformSyncer()
        stats = syncer.sync_data(erms_records)
        self.stderr.write(self.style.WARNING(f'Import stats: {stats}'))
