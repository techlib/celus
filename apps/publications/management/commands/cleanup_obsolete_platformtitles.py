import logging
from time import time

from django.core.management.base import BaseCommand
from publications.logic.cleanup import clean_obsolete_platform_title_links

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Removes platform-title links that are no longer valid because logs were removed'

    def add_arguments(self, parser):
        parser.add_argument('--do-it', dest='do_it', action='store_true')

    def handle(self, *args, **options):
        start = time()
        pretend = not options['do_it']
        if pretend:
            self.stderr.write('Just counting, use --do-it to really perform delete\n')
        stats = clean_obsolete_platform_title_links(pretend=pretend)
        logger.info('Duration: %s, Stats: %s', time() - start, stats)
