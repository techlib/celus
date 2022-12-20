import logging
from collections import Counter
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from sushi.models import SushiFetchAttempt

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = (
        'Goes over the queued sushi attempts which should have an associated file and '
        'checks that the file exists. If not, it can remove the attempts'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '-d', dest='delete', action='store_true', help='delete attempts with missing files'
        )

    def handle(self, *args, **options):
        stats = Counter()
        to_delete = []
        for attempt in SushiFetchAttempt.objects.filter(data_file__isnull=False).exclude(
            data_file__exact=""
        ):
            filepath = Path(settings.MEDIA_ROOT) / attempt.data_file.name
            if filepath.exists():
                stats['exists'] += 1
            else:
                stats['missing'] += 1
                logger.debug('Missing: %s', filepath)
                to_delete.append(attempt.pk)
        logger.info('Stats: %s', stats)
        if to_delete:
            if options['delete']:
                logger.info('Deleting %d fetch attempts', stats['missing'])
                SushiFetchAttempt.objects.filter(pk__in=to_delete).delete()
            else:
                logger.info('Nothing deleted - use "-d" to delete attempts with missing files')
