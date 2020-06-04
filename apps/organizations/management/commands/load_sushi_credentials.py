import logging

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from sushi.logic.data_import import import_sushi_credentials_from_csv

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Load SUSHI credentials from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('file', help='CSV file to import')

    @atomic
    def handle(self, *args, **options):
        stats = import_sushi_credentials_from_csv(
            options['file'],
            reversion_comment='Updated/created by command line script "load_sushi_credentials"',
        )
        self.stderr.write(self.style.WARNING(f'Import stats: {stats}'))
