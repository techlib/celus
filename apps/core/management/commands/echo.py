import logging
from argparse import FileType

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    This command is intended to be used for testing purposes only. It is used to test the
    management command API.
    """

    help = 'Echo the given string to stdout or stderr'

    def add_arguments(self, parser):
        parser.add_argument('echo', help='String to be returned back', type=str)
        parser.add_argument(
            '-e',
            dest='error',
            action='store_true',
            help='When given, echo will be printed to stderr instead of stdout',
        )
        parser.add_argument(
            '-f',
            dest='file',
            type=FileType('r', encoding='utf-8'),
            help='When given, the contents of the file will be echoed instead of the string',
        )
        parser.add_argument('--do-it', dest='doit', action='store_true')

    def handle(self, *args, **options):
        logger.info('Starting echo command')
        sink = self.stderr if options['error'] else self.stdout
        content = options['file'].read() if options['file'] else options['echo']
        sink.write(content)
        if not options['doit']:
            raise ValueError('not doing it')
