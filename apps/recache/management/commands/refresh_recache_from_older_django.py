import logging

import django
from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from ...models import CachedQuery
from ...tasks import renew_cached_query_task

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = (
        'Looks at all the cached queries and plans their update to current Django. Is meant '
        'to be run during updates'
    )

    @atomic
    def handle(self, *args, **options):
        current_caches = {
            cq.query_hash for cq in CachedQuery.objects.filter(django_version=django.get_version())
        }
        for cq in CachedQuery.objects.exclude(django_version=django.get_version()):
            if cq.query_hash not in current_caches:
                logger.debug('Scheduling renewal of %s', cq)
                renew_cached_query_task.apply_async(args=(cq.pk,))
            else:
                logger.info('Current cache already exists: removing %s', cq)
                cq.delete()
