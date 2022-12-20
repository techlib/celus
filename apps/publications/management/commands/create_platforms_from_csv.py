import csv
import logging
from collections import Counter

from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from publications.models import Platform

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Create/sync platforms with CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file')
        parser.add_argument('--do-it', dest='doit', action='store_true')

    @atomic
    def handle(self, *args, **options):
        stats = Counter()
        with open(options['csv_file'], 'r') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                name = row.get('name')
                if not name:
                    raise ValueError('Row "name" is required')
                name = name.strip()
                short_name = row.get('short_name', name)
                platform_params = {'short_name': short_name}
                _, created = Platform.objects.update_or_create(name=name, defaults=platform_params)
                if created:
                    stats['platform_created'] += 1
                    logger.debug('created platform %s: %s', name, platform_params)
                else:
                    stats['platform_existed'] += 1
                    logger.debug('updating platform %s: %s', name, platform_params)

        self.stderr.write(self.style.WARNING(f'Import stats: {stats}'))
        if not options['doit']:
            raise ValueError('preventing db commit, use --do-it to really do it ;)')
