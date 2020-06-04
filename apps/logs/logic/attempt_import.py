import logging
import os
import traceback

from django.conf import settings
from django.db.transaction import atomic

from logs.logic.data_import import import_counter_records
from logs.models import OrganizationPlatform, ImportBatch
from nigiri.client import Sushi5Client, SushiException, SushiError
from sushi.models import SushiFetchAttempt


logger = logging.getLogger(__name__)


def import_new_sushi_attempts():
    queryset = SushiFetchAttempt.objects.filter(
        is_processed=False, download_success=True, contains_data=True, import_crashed=False
    )
    count = queryset.count()
    logger.info('Found %d unprocessed successful download attempts matching criteria', count)
    for i, attempt in enumerate(queryset):
        logger.info('----- Importing attempt #%d -----', i)
        try:
            import_one_sushi_attempt(attempt)
        except Exception as e:
            # we catch any kind of error to make sure that the loop does not die
            logger.error('Importing sushi attempt #%d crashed: %s', attempt.pk, e)
            attempt.mark_crashed(e)


def validate_data_v5(data):
    Sushi5Client.validate_data(data)


def validate_data_v4(data):
    return None


@atomic
def import_one_sushi_attempt(attempt: SushiFetchAttempt):
    counter_version = attempt.credentials.counter_version
    reader_cls = attempt.counter_report.get_reader_class()
    if not reader_cls:
        logger.warning('Unsupported report type %s', attempt.counter_report.code)
        return
    logger.debug('Processing file: %s', attempt.data_file.name)
    reader = reader_cls()
    try:
        data = reader.file_to_input(os.path.join(settings.MEDIA_ROOT, attempt.data_file.name))
    except FileNotFoundError as e:
        logger.error('Cannot find the referenced file - probably deleted?: %s', e)
        attempt.mark_crashed(e)
        return
    validator = validate_data_v4 if counter_version == 4 else validate_data_v5
    try:
        validator(data)
    except SushiException as e:
        # if we find validation error on data revalidation, we switch the report success attr
        logger.error('Validation error: %s', e)
        logger.info('Marking the attempt as unsuccessful')
        attempt.download_success = True
        attempt.processing_success = True
        attempt.is_processed = True
        attempt.import_crashed = True
        attempt.contains_data = False
        if isinstance(e.text, SushiError):
            attempt.log = str(e.text)
            attempt.error_code = e.text.code
        else:
            attempt.log = str(e)
        attempt.save()
        return
    # we need to create explicit connection between organization and platform
    op, created = OrganizationPlatform.objects.get_or_create(
        platform=attempt.credentials.platform, organization=attempt.credentials.organization
    )
    if created:
        logger.debug(
            'Created Organization-Platform connection between %s and %s',
            op.organization,
            op.platform,
        )
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
            import_batch,
        )
        attempt.import_batch = import_batch
        logger.info('Import stats: %s', stats)
    else:
        if reader.errors or reader.warnings:
            if reader.errors:
                attempt.log = '; '.join(str(e) for e in reader.errors)
                logger.warning('Found errors: %s', attempt.log)
                attempt.error_code = reader.errors[0].code
            else:
                attempt.log = 'Warnings: {}'.format('; '.join(str(w) for w in reader.warnings))
                attempt.error_code = reader.warnings[0].code
            attempt.download_success = True
            attempt.contains_data = False
            error_explanation = Sushi5Client.explain_error_code(attempt.error_code)
            attempt.queued = error_explanation.should_retry and error_explanation.setup_ok
            attempt.processing_success = not (
                error_explanation.needs_checking and error_explanation.setup_ok
            )
            attempt.save()
        else:
            attempt.contains_data = False
            attempt.log = 'No data found during import'
            attempt.save()
        logger.warning('No records found!')
    attempt.mark_processed()


def reprocess_attempt(attempt: SushiFetchAttempt) -> SushiFetchAttempt:
    attempt.unprocess()
    try:
        import_one_sushi_attempt(attempt)
    except Exception as e:
        # we catch any kind of error to make sure that there is no crash
        logger.error('Importing sushi attempt #%d crashed: %s', attempt.pk, e)
        attempt.mark_crashed(e)
    return attempt
