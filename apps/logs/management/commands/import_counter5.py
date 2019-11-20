import json
import logging
from time import time

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from logs.models import ImportBatch
from publications.models import Platform
from ...logic.data_import import import_counter_records
from ...models import ReportType, OrganizationPlatform
from organizations.models import Organization
from nigiri.counter5 import Counter5TRReport

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Import data from a COUNTER 5 JSON file into the database'

    def add_arguments(self, parser):
        parser.add_argument('organization',
                            help='The ID or name of organization for which this data was '
                                 'downloaded')
        parser.add_argument('platform',
                            help='Short name of platform for which data was downloaded')
        parser.add_argument('report_type', help='Report type of the submitted data')
        parser.add_argument('file', help='Input file with COUNTER 5 formatted data')

    @atomic
    def handle(self, *args, **options):
        t1 = time()
        with open(options['file'], 'r', encoding='utf-8') as infile:
            data = json.load(infile)
        reader = Counter5TRReport()
        organization = Organization.objects.get(internal_id=options['organization'])
        platform = Platform.objects.get(short_name=options['platform'])
        op, created = OrganizationPlatform.objects.get_or_create(platform=platform,
                                                                 organization=organization)
        if created:
            self.stderr.write(self.style.SUCCESS(
                f'Created Organization-Platform connection between {organization} and {platform}'
            ))
        report_type = ReportType.objects.get(short_name=options['report_type'])
        self.stderr.write(f'Time #1: {time()-t1}\n')
        t2 = time()
        records = reader.read_report(data)
        self.stderr.write(f'Time #2: {time() - t2}\n')
        t3 = time()
        import_batch = ImportBatch.objects.create(organization=organization, platform=platform,
                                                  report_type=report_type)
        stats = import_counter_records(report_type, organization, platform, records, import_batch)
        self.stderr.write(f'Time #3: {time() - t3}\n')
        self.stderr.write(self.style.WARNING(f'Import stats: {stats}'))
        self.stderr.write(self.style.WARNING(f'Import batch ID: #{import_batch.pk}'))

