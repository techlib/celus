import json
import logging
import os

from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from django.conf import settings

from pycounter import report

from nigiri.client import Sushi5Client, SushiException
from sushi.models import SushiFetchAttempt
from ...logic.data_import import import_counter_records
from ...models import ReportType, OrganizationPlatform
from nigiri.counter5 import Counter5TRReport
from nigiri.counter4 import Counter4JR1Report

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Import all data from yet unprocessed SushiFetchAttempts'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        count = SushiFetchAttempt.objects.filter(is_processed=False, success=True).count()
        logger.info('Found %d unprocessed successful download attempts', count)
        for i, attempt in enumerate(SushiFetchAttempt.objects.filter(is_processed=False,
                                                                     success=True)):
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
        if not data:
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
        stats = import_counter_records(
            attempt.counter_report.report_type,
            attempt.credentials.organization,
            attempt.credentials.platform,
            records)
        attempt.mark_processed()
        self.stderr.write(self.style.WARNING(f'Import stats: {stats}'))

    def get_reader_v4(self, attempt: SushiFetchAttempt):
        if attempt.counter_report.report_type.short_name == 'JR1':
            return Counter4JR1Report()
        else:
            self.stderr.write(self.style.NOTICE(
                f'Unsupported report type {attempt.counter_report.report_type}'))
            return None

    def get_reader_v5(self, attempt: SushiFetchAttempt):
        if attempt.counter_report.report_type.short_name == 'TR':
            return Counter5TRReport()
        else:
            self.stderr.write(self.style.NOTICE(
                f'Unsupported report type {attempt.counter_report.report_type}'))
            return None

    @classmethod
    def file_to_data_v4(cls, file):
        return report.parse(os.path.join(settings.MEDIA_ROOT, file.name))

    @classmethod
    def file_to_data_v5(cls, file):
        data = json.load(file)
        try:
            Sushi5Client.validate_data(data)  # we re-validate downloaded data
        except SushiException as e:
            return None
        return data
