import csv
import logging
from collections import Counter

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from organizations.models import Organization

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Create/sync organizations with CSV file'

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
                org_params = {'short_name': short_name}
                for extra_attr in ['name_cs', 'ext_id', 'internal_id']:
                    if ext_value := row.get(extra_attr):
                        org_params[extra_attr] = ext_value
                _, created = Organization.objects.update_or_create(defaults=org_params, name=name)
                if created:
                    stats['organization_created'] += 1
                    logger.debug('created organization %s: %s', name, org_params)
                else:
                    stats['organization_existed'] += 1
                    logger.debug('updating organization %s: %s', name, org_params)

        self.stderr.write(self.style.WARNING(f'Import stats: {stats}'))
        if not options['doit']:
            raise ValueError('preventing db commit, use --do-it to really do it ;)')
