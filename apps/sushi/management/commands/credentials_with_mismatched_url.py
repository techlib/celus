import csv
import logging
from collections import Counter
from io import StringIO

from django.core.management.base import BaseCommand
from publications.models import Platform
from sushi.models import SushiCredentials

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = (
        'Finds all SUSHI credentials where the platform has URL from brain and the credentials '
        'use some other URL.'
    )

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        stats = Counter()
        out = StringIO()
        writer = csv.DictWriter(
            out,
            fieldnames=[
                'platform',
                'organization',
                'counter_version',
                'verified',
                'url',
                'brain_url',
            ],
        )
        writer.writeheader()
        for platform in Platform.objects.filter(knowledgebase__providers__isnull=False):
            for provider in platform.knowledgebase['providers']:
                if (url := provider.get('provider', {}).get('url')) and (
                    counter_version := provider.get('counter_version')
                ):
                    for cred in (
                        SushiCredentials.objects.filter(
                            platform=platform, counter_version=counter_version
                        )
                        .exclude(url=url)
                        .annotate_verified()
                        .select_related('organization')
                    ):
                        if cred.url.rstrip('/') != url.rstrip('/'):
                            stats[f'{platform.pk}-{platform.short_name}'] += 1
                            writer.writerow(
                                {
                                    'platform': platform.short_name,
                                    'organization': cred.organization.short_name,
                                    'counter_version': counter_version,
                                    'url': cred.url,
                                    'brain_url': url,
                                    'verified': cred.verified,
                                }
                            )

        logger.info('Stats: %s', stats)
        logger.info('Total mismatches: %d', sum(stats.values()))
        self.stdout.write(out.getvalue())
