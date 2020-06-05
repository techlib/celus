import logging

from django.core.management.base import BaseCommand

from sushi.logic.fetching import retry_queued

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Goes over the queued sushi attempts and redownloads them where needed'

    def add_arguments(self, parser):
        parser.add_argument(
            '-n', dest='number', type=int, default=0, help='number of attempts to process'
        )

    def handle(self, *args, **options):
        stats = retry_queued(number=options['number'], sleep_interval=2)
        self.stderr.write(self.style.SUCCESS(f'Stats: {stats}'))
