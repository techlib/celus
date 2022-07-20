import json
import logging

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from pycounter import report

from publications.models import Platform
from celus_nigiri.counter4 import Counter4JR1Report
from ...logic.data_import import import_counter_records
from ...models import ReportType, OrganizationPlatform
from organizations.models import Organization

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Import data from a COUNTER 4 TSV file into the database'

    def add_arguments(self, parser):
        parser.add_argument(
            'organization',
            help='The ID or name of organization for which this data was ' 'downloaded',
        )
        parser.add_argument('platform', help='Short name of platform for which data was downloaded')
        parser.add_argument('report_type', help='Report type of the submitted data')
        parser.add_argument('file', help='Input file with COUNTER 4 formatted data')

    @atomic
    def handle(self, *args, **options):
        data = report.parse(options['file'])
        organization = Organization.objects.get(internal_id=options['organization'])
        platform = Platform.objects.get(short_name=options['platform'])
        op, created = OrganizationPlatform.objects.get_or_create(
            platform=platform, organization=organization
        )
        if created:
            self.stderr.write(
                self.style.SUCCESS(
                    f'Created Organization-Platform connection between {organization} and {platform}'
                )
            )
        report_type = ReportType.objects.get(short_name=options['report_type'])
        reader = Counter4JR1Report()
        records = reader.read_report(data)
        stats = import_counter_records(report_type, organization, platform, records)
        self.stderr.write(self.style.WARNING(f'Import stats: {stats}'))
