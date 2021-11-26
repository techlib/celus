import logging
from collections import Counter

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from django_celery_results.models import TaskResult
from error_report.models import Error

from activity.models import UserActivity
from annotations.models import Annotation
from export.models import FlexibleDataExport
from knowledgebase.models import RouterSyncAttempt, PlatformImportAttempt
from logs.models import ImportBatch, DimensionText, Dimension
from organizations.models import Organization
from publications.models import Title
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
        # remove unused data
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
            Title,
            UserActivity,
            RouterSyncAttempt,
            TaskResult,
            PlatformImportAttempt,
        ):
            self.stderr.write(self.style.WARNING(f'Deleting {model.__name__}'))
            count, details = model.objects.all().delete()
            self.update_stats(stats, details)
            self.stderr.write(self.style.WARNING(f'  - deleted: {count} objects'))
        # remove some dimension texts
        for dim_name in ('Publisher', 'Success'):
            try:
                dim = Dimension.objects.get(short_name=dim_name)
            except Dimension.DoesNotExist:
                pass
            else:
                count, details = DimensionText.objects.filter(dimension=dim).delete()
                self.update_stats(stats, details)
                self.stderr.write(
                    self.style.WARNING(f'Deleted {count} DimensionTexts for dim "{dim_name}"')
                )
        self.stderr.write(self.style.WARNING(f'Delete stats: '))
        for key, value in sorted(stats.items()):
            self.stderr.write(self.style.WARNING(f'  {key}: {value}'))
        # fix other things
        site = Site.objects.get(pk=settings.SITE_ID)
        host_name = settings.ALLOWED_HOSTS[0]
        if site.name != host_name or site.domain != host_name:
            site.name = host_name
            site.domain = host_name
            self.stderr.write(
                self.style.SUCCESS(f'Updating site object to host name "{host_name}"')
            )
            site.save()
        # create consortium organization
        for org_id in settings.MASTER_ORGANIZATIONS:
            Organization.objects.create(internal_id=org_id, short_name=org_id, name=org_id)
            self.stderr.write(self.style.SUCCESS(f'Created organization "{org_id}"'))

        if not options['doit']:
            raise ValueError('preventing db commit, use --do-it to really do it ;)')
