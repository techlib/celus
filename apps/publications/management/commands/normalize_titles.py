import logging
from collections import Counter

from django.core.management.base import BaseCommand
from django.db import DatabaseError
from logs.logic.validation import normalize_isbn, normalize_issn, normalize_title
from publications.models import Title

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Go over all titles and normalize their name, isbn and issns'

    def add_arguments(self, parser):
        parser.add_argument('--do-it', dest='do_it', action='store_true')

    def handle(self, *args, **options):
        stats = Counter()

        for title in Title.objects.all().iterator():
            stats['total'] += 1
            new_issn = title.issn and normalize_issn(title.issn, raise_error=False)
            new_eissn = title.eissn and normalize_issn(title.eissn, raise_error=False)
            new_isbn = title.isbn and normalize_isbn(title.isbn)
            new_name = normalize_title(title.name)
            if (
                new_issn != title.issn
                or new_isbn != title.isbn
                or new_name != title.name
                or new_eissn != title.eissn
            ):
                stats['normalized'] += 1
                if options['do_it']:
                    title.isbn = new_isbn
                    title.issn = new_issn
                    title.eissn = new_eissn
                    title.name = new_name
                    try:
                        title.save()
                    except DatabaseError as e:
                        stats['errors'] += 1
        logger.info('Stats: %s', stats)
        if stats['errors']:
            logger.info(
                'Potential errors are caused by duplicate titles causing database constraint '
                'violations'
            )
        if not options['do_it']:
            logger.warning('Nothing has changed - to do the changes use --do-it')
