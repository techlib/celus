import json
import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Goes through the SUSHI data and checks that they are OK'

    def add_arguments(self, parser):
        parser.add_argument('file', help='JSON file to process')

    def handle(self, *args, **options):
        with open(options['file'], 'r') as infile:
            data = json.load(infile)
        header = data.get('Report_Header')
        if not header:
            logger.warning('Missing report header')
        else:
            exceptions = header.get('Exceptions', [])
            for exception in exceptions:
                logger.error('Exception: %s', exception)
        items = data.get('Report_Items')
        if not items:
            logger.error('No Report_Items key!')
        else:
            for i, item in enumerate(items):
                if 'Title' not in item:
                    logger.error('Missing title in item #%s: %s', i, item)






