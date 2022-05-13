import csv
import logging
from collections import Counter
from io import StringIO
from time import monotonic

from django.contrib.postgres.aggregates import ArrayAgg
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Min, Q, F, Value, Exists, OuterRef
from django.db.models.functions import Concat
from django.db.transaction import atomic

from logs.logic.reimport import (
    find_import_batches_to_reimport,
    reimport_import_batch_with_fa,
    SourceFileMissingError,
    has_source_data_file,
    reimport_mdu_batch,
)
from logs.models import ImportBatch, AccessLog
from publications.models import Title
from sushi.models import SushiCredentials

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = (
        'Helper script for reimport which fixes titles erroneously mixed together. It contains '
        'code for two stages of the process - preparation and cleanup.'
    )

    title_prefix = '_foo42_'

    def add_arguments(self, parser):
        parser.add_argument('--do-it', dest='do_it', action='store_true')
        parser.add_argument(
            'phase', choices=['prepare', 'cleanup'], help='Which phase should be run'
        )

    @atomic
    def handle(self, *args, **options):
        if options['phase'] == 'prepare':
            self.prepare()
        elif options['phase'] == 'cleanup':
            self.cleanup()
        if not options['do_it']:
            raise CommandError('Not doing anything - use --do-it to really make the changes')

    def prepare(self):
        """
        adds a prefix to all title names so that it will not be using during reimport and
        can be easily recognized afterwards.
        """
        if Title.objects.filter(name__startswith=self.title_prefix).exists():
            raise CommandError(
                f'Some title with "{self.title_prefix}" prefix already exists - the prepare phase '
                f'was already performed'
            )
        info = Title.objects.update(name=Concat(Value(self.title_prefix), F('name')))
        logger.info(f'Updated {info} records')

    def cleanup(self):
        """
        Remove all titles which are not references from elsewhere.
        """
        deleted = Title.objects.filter(
            ~Exists(AccessLog.objects.filter(target_id=OuterRef('pk')))
        ).delete()
        logger.info(f'Deleted: {deleted}')
        foo_count = Title.objects.filter(name__startswith=self.title_prefix).count()
        logger.info(f'Original titles with prefix still existing: {foo_count}')
        if foo_count:
            for title in Title.objects.filter(name__startswith=self.title_prefix).annotate(
                al_count=Count('accesslog'),
                ibs=ArrayAgg('accesslog__import_batch_id', distinct=True),
            ):
                logger.info(f'{title.pk},{title.name},{title.al_count},{title.ibs}')
