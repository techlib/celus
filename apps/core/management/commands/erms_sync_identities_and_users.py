import logging

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from core.models import DataSource
from ...logic.sync import sync_identities_with_erms, sync_users_with_erms

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Sync organizations between ERMS and the database'

    def add_arguments(self, parser):
        pass

    @atomic
    def handle(self, *args, **options):
        data_source, _created = DataSource.objects.get_or_create(
            short_name='ERMS', type=DataSource.TYPE_API
        )
        stats = sync_users_with_erms(data_source)
        self.stderr.write(self.style.WARNING(f'User import stats: {stats}'))
        stats = sync_identities_with_erms(data_source)
        self.stderr.write(self.style.WARNING(f'Identity import stats: {stats}'))
