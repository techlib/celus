import logging
from argparse import FileType

from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from sushi.logic.data_import import import_sushi_credentials_from_csv

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Load SUSHI credentials from a CSV file'

    def add_arguments(self, parser):
        # we use a named argument because it is then possible to pass an open file from python
        # code instead of a file path - this makes it easier to use this command from the API
        # (call_command runs *args through argparse, while **kwargs are passed directly:
        # https://docs.djangoproject.com/en/3.2/ref/django-admin/#django.core.management.call_command
        # )
        # for the same reason, the argument is not required - otherwise argparse would complain
        parser.add_argument(
            '-f',
            dest='file',
            help='CSV file to import',
            type=FileType('r', encoding='utf-8'),
        )
        parser.add_argument('--do-it', dest='doit', action='store_true')
        parser.add_argument(
            '-k',
            dest='knowledgebase_urls',
            action='store_true',
            help='If available, use knowledgebase urls instead of the ones stored in the file',
        )

    @atomic
    def handle(self, *args, **options):
        stats = import_sushi_credentials_from_csv(
            options['file'],
            prefer_knowledgebase_urls=options['knowledgebase_urls'],
            reversion_comment='Updated/created by command line script "load_sushi_credentials"',
        )
        self.stderr.write(self.style.WARNING(f'Import stats: {stats}'))
        if not options['doit']:
            raise ValueError('preventing db commit, use --do-it to really do it ;)')
