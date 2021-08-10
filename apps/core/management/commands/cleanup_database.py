import logging
from collections import Counter

from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from error_report.models import Error

from annotations.models import Annotation
from export.models import FlexibleDataExport
from logs.models import ImportBatch
from organizations.models import Organization
from recache.models import CachedQuery
from scheduler.models import Harvest, Scheduler

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = (
        'Cleanup all the organizations and their data from the database. Used when you copy an '
        'existing db into a new install and want to clean it up.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--do-it', dest='doit', action='store_true')

    @classmethod
    def update_stats(cls, stats, details):
        for key, value in details.items():
            stats[key] += value

    @atomic
    def handle(self, *args, **options):
        stats = Counter()
        for model in (
            ImportBatch,
            Organization,
            Annotation,
            Error,
            FlexibleDataExport,
            CachedQuery,
            Harvest,
            Scheduler,
        ):
            self.stderr.write(self.style.WARNING(f'Deleting {model.__name__}'))
            count, details = model.objects.all().delete()
            self.update_stats(stats, details)
            self.stderr.write(self.style.WARNING(f'Deleted: {count} objects; stats: {stats}'))
        if not options['doit']:
            self.stderr.write(self.style.WARNING(f'Stats: {stats}'))
            raise ValueError('preventing db commit, use --do-it to really do it ;)')
