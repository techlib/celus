import logging

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from publications.logic.title_management import find_mergeable_titles, merge_titles

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Go over all titles and merge those which represent the same title'

    def add_arguments(self, parser):
        parser.add_argument('--do-it', dest='do_it', action='store_true')

    @atomic
    def handle(self, *args, **options):
        count = 0
        for titles in find_mergeable_titles():
            print('------------')
            for title in titles:
                print(
                    ', '.join(
                        map(
                            str,
                            [
                                title.pk,
                                title.name,
                                title.pub_type,
                                title.issn,
                                title.eissn,
                                title.isbn,
                                title.doi,
                                title.proprietary_ids,
                            ],
                        )
                    )
                )
            count += 1
            if options['do_it']:
                merge_titles(titles)
        logger.info('Total count: %d', count)
        if not options['do_it']:
            logger.warning('Nothing has changed - for merge use --do-it')
