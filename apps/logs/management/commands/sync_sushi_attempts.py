import logging

from django.core.management.base import BaseCommand
from django.models.transaction import atomic

from logs.logic.attempt_import import import_one_sushi_attempt
from sushi.models import SushiFetchAttempt, AttemptStatus

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Import all data from yet unprocessed SushiFetchAttempts'

    def add_arguments(self, parser):
        parser.add_argument('-r', dest='report_type', help='code of the counter report to fetch')
        parser.add_argument(
            '-n', dest='number_of_items', type=int, help='number of attempts to process'
        )

    @atomic
    def handle(self, *args, **options):
        queryset = SushiFetchAttempt.objects.select_for_update(skip_locked=True).filter(
            status=AttemptStatus.IMPORTING,
        )
        if options['report_type']:
            queryset = queryset.filter(counter_report__code=options['report_type'])
        count = queryset.count()
        if options['number_of_items']:
            queryset = queryset[: options['number_of_items']]
        logger.info('Found %d unprocessed successful download attempts matching criteria', count)
        for i, attempt in enumerate(queryset):
            logger.info('----- Attempt #%d -----', i)
            import_one_sushi_attempt(attempt)
