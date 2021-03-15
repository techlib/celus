import json
import logging

from django.core.management.base import BaseCommand

from nigiri.counter5 import Counter5TRReport

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Goes through the SUSHI data and checks that they are OK'

    def add_arguments(self, parser):
        parser.add_argument('file', help='JSON file to process')

    def handle(self, *args, **options):
        with open(options['file'], 'r', encoding='utf-8') as infile:
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
            seen_data = {}
            for i, item in enumerate(items):
                if 'Title' not in item:
                    logger.error('Missing title in item #%s: %s', i, item)
                item_key = self.item_to_key(item)
                if item_key in seen_data:
                    logger.warning(
                        'Clashing data for key %s in record #%d', item_key, seen_data[item_key]
                    )
                    logger.info('  #%d: %s', seen_data[item_key], items[seen_data[item_key]])
                    logger.info('  #%d: %s', i, item)
                else:
                    seen_data[item_key] = i
            logger.info('Found %d records', i + 1)

    @classmethod
    def item_to_key(cls, item):
        key_keys = ['Title', 'Platform']
        item_key = [item.get(key) for key in key_keys]
        item_ids = item.get('Item_ID') or []
        for key in Counter5TRReport.allowed_item_ids:
            for item_id in item_ids:
                if item_id.get('Type') == key:
                    item_key.append(item_id.get('Value'))
                    break
        item_key += [item.get(key) for key in Counter5TRReport.dimensions]
        return tuple(item_key)
