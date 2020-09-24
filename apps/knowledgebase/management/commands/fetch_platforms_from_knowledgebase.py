import logging

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from core.models import DataSource
from knowledgebase.models import PlatformImportAttempt

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Fetches platforms from given knowledgebase data source'

    def add_arguments(self, parser):
        parser.add_argument('-s', '--source', dest='source', help="data source name", required=True)
        parser.add_argument(
            '-m',
            '--merge',
            dest='merge',
            choices=[e.name for e in PlatformImportAttempt.MergeStrategy],
            default=PlatformImportAttempt.MergeStrategy.NONE.name,
        )
        parser.add_argument('--do-it', dest='doit', action='store_true')

    @atomic
    def handle(self, *args, **options):
        source = DataSource.objects.get(
            short_name=options["source"], type=DataSource.TYPE_KNOWLEDGEBASE
        )

        logger.info(
            "Fetching and processing platforms from %s (merge_strategy=%s)",
            source,
            options['merge'],
        )
        attempt = PlatformImportAttempt.objects.create(source=source)
        attempt.perform(PlatformImportAttempt.MergeStrategy[options['merge']])
        logger.info("Success")
        if attempt.stats:
            print(attempt.stats)
        else:
            print("No new data")
        if not options['doit']:
            raise ValueError('preventing db commit, use --do-it to really do it ;)')
