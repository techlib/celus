import csv
import logging
import re
from collections import Counter

from core.models import DataSource
from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from publications.models import Platform

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Add registry ID to platforms from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file')
        parser.add_argument('--do-it', dest='doit', action='store_true')

    @atomic
    def handle(self, *args, **options):
        stats = Counter()
        erms_source = DataSource.objects.get(short_name='ERMS', type=DataSource.TYPE_API)
        ext_id_to_platform = {p.ext_id: p for p in Platform.objects.all()}
        seen_registry_ids = {str(p.counter_registry_id) for p in ext_id_to_platform.values()}
        with open(options['csv_file'], 'r') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                ext_id = int(row.get('ext_id').strip())
                platform = ext_id_to_platform.get(ext_id)
                if not platform:
                    logger.warning('Platform with ext_id=%s not found', ext_id)
                    stats['no_platform'] += 1
                    continue

                registry_url = row.get('registry URL').strip()
                if not registry_url or registry_url == '-':
                    logger.debug('Platform with ext_id=%s has no registry URL', ext_id)
                    stats['no_registry_url'] += 1
                    continue

                registry_id = re.match(
                    r'^https://registry.projectcounter.org/platform/([-0-9a-f]+)$', registry_url
                ).group(1)
                if str(platform.counter_registry_id) == registry_id:
                    logger.debug('Platform with ext_id=%s has correct registry ID', ext_id)
                    stats['same_registry_id'] += 1
                    continue

                if platform.source != erms_source:
                    logger.warning('Platform with ext_id=%s does not have ERMS source', ext_id)
                    stats['wrong_source'] += 1
                    continue

                if registry_id in seen_registry_ids:
                    logger.warning('Platform with ext_id=%s has duplicate registry ID', ext_id)
                    stats['duplicate_registry_id'] += 1
                    continue
                platform.counter_registry_id = registry_id
                logger.info('Adding registry ID to platform with ext_id=%s', ext_id)
                platform.save()
                seen_registry_ids.add(registry_id)
                stats['updated'] += 1

        self.stderr.write(self.style.WARNING(f'Stats: {stats}'))
        if not options['doit']:
            raise ValueError('preventing db commit, use --do-it to really do it ;)')
