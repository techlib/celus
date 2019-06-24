import json
import logging

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from logs.models import ReportType
from sushi.counter5 import Counter5TRReport

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Import data from a COUNTER 5 JSON file into the database'

    def add_arguments(self, parser):
        parser.add_argument('organization',
                            help='The ID or name of organization for which this data was '
                                 'downloaded')
        parser.add_argument('report_type', help='Report type of the submitted data')
        parser.add_argument('file', help='Input file with COUNTER 5 formatted data')

    @atomic
    def handle(self, *args, **options):
        with open(options['file'], 'r') as infile:
            data = json.load(infile)
        reader = Counter5TRReport()
        report_type = ReportType.objects.get(short_name=options['report_type'])
        records = reader.read_report(data)

