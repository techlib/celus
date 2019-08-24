import json
import logging
import os

from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from django.conf import settings

from pycounter import report

from logs.models import ImportBatch
from nigiri.client import Sushi5Client, SushiException
from sushi.models import SushiFetchAttempt
from ...logic.data_import import import_counter_records
from ...models import ReportType, OrganizationPlatform
from nigiri.counter5 import Counter5TRReport, Counter5DRReport, Counter5PRReport
from nigiri.counter4 import Counter4JR1Report, Counter4BR2Report

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Import all data from yet unprocessed SushiFetchAttempts'

    def add_arguments(self, parser):
        parser.add_argument('-r', dest='report_type', help='code of the counter report to fetch')
        parser.add_argument('-n', dest='number_of_items', type=int,
                            help='number of attempts to process')

    def handle(self, *args, **options):
        queryset = SushiFetchAttempt.objects.filter(is_processed=False, success=True)
        if options['report_type']:
            queryset = queryset.filter(counter_report__code=options['report_type'])
        count = queryset.count()
        if options['number_of_items']:
            queryset = queryset[:options['number_of_items']]
        logger.info('Found %d unprocessed successful download attempts matching criteria', count)
        for i, attempt in enumerate(queryset):
            logger.info('----- Attempt #%d -----', i)
            self.process_one_attempt(attempt)

    @atomic
    def process_one_attempt(self, attempt):
        counter_version = attempt.credentials.counter_version
        get_reader = getattr(self, f'get_reader_v{counter_version}')
        reader = get_reader(attempt)
        if not reader:
            return
        self.stderr.write(self.style.NOTICE(f'Processing file: {attempt.data_file.name}'))
        file_to_data = getattr(self, f'file_to_data_v{counter_version}')
        data = file_to_data(attempt.data_file)
        validator = getattr(self, f'validate_data_v{counter_version}')
        try:
            validator(data)
        except SushiException as e:
            # if we find validation error on data revalidation, we switch the report success attr
            logger.error('Validation error: %s', e)
            logger.info('Marking the attempt as unsuccessful')
            attempt.success = False
            if attempt.log:
                attempt.log += '\n'
            attempt.log += str(e)
            attempt.save()
            return
        # we need to create explicit connection between organization and platform
        # TODO: really?
        op, created = OrganizationPlatform.objects.get_or_create(
            platform=attempt.credentials.platform,
            organization=attempt.credentials.organization
        )
        if created:
            self.stderr.write(self.style.SUCCESS(
                f'Created Organization-Platform connection between {op.organization} '
                f'and {op.platform}'
            ))
        # now read the data and import it
        records = reader.read_report(data)
        if records:
            import_batch = ImportBatch.objects.create(
                platform=attempt.credentials.platform,
                organization=attempt.credentials.organization,
                report_type=attempt.counter_report.report_type,
            )
            stats = import_counter_records(
                attempt.counter_report.report_type,
                attempt.credentials.organization,
                attempt.credentials.platform,
                records,
                import_batch)
            attempt.import_batch = import_batch
            self.stderr.write(self.style.WARNING(f'Import stats: {stats}'))
        else:
            self.stderr.write(self.style.ERROR(f'No records found!'))
        attempt.mark_processed()

    def get_reader_v4(self, attempt: SushiFetchAttempt):
        if attempt.counter_report.report_type.short_name == 'JR1':
            return Counter4JR1Report()
        elif attempt.counter_report.report_type.short_name == 'BR2':
            return Counter4BR2Report()
        else:
            self.stderr.write(self.style.NOTICE(
                f'Unsupported report type {attempt.counter_report.report_type}'))
            return None

    def get_reader_v5(self, attempt: SushiFetchAttempt):
        if attempt.counter_report.report_type.short_name == 'TR':
            return Counter5TRReport()
        elif attempt.counter_report.report_type.short_name == 'DR':
            return Counter5DRReport()
        elif attempt.counter_report.report_type.short_name == 'PR':
            return Counter5PRReport()
        else:
            self.stderr.write(self.style.NOTICE(
                f'Unsupported report type {attempt.counter_report.report_type}'))
            return None

    @classmethod
    def file_to_data_v4(cls, file):
        return report.parse(os.path.join(settings.MEDIA_ROOT, file.name))

    @classmethod
    def file_to_data_v5(cls, file):
        return json.load(file)

    @classmethod
    def validate_data_v5(cls, data):
        Sushi5Client.validate_data(data)

    @classmethod
    def validate_data_v4(cls, data):
        return None
