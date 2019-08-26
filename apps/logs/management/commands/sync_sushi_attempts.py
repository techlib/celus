import json
import logging
import os

from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from django.conf import settings

from logs.models import ImportBatch
from nigiri.client import Sushi5Client, SushiException
from sushi.models import SushiFetchAttempt
from ...logic.data_import import import_counter_records
from ...models import OrganizationPlatform

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
    def process_one_attempt(self, attempt: SushiFetchAttempt):
        counter_version = attempt.credentials.counter_version
        reader_cls = attempt.counter_report.get_reader_class()
        if not reader_cls:
            self.stderr.write(self.style.NOTICE(
                f'Unsupported report type {attempt.counter_report.code}'))
            return
        self.stderr.write(self.style.NOTICE(f'Processing file: {attempt.data_file.name}'))
        reader = reader_cls()
        data = reader.file_to_input(os.path.join(settings.MEDIA_ROOT, attempt.data_file.name))
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

    @classmethod
    def validate_data_v5(cls, data):
        Sushi5Client.validate_data(data)

    @classmethod
    def validate_data_v4(cls, data):
        return None
