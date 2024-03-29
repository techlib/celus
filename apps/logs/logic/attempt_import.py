import logging
import os
import typing
from datetime import date
from time import time

from celus_nigiri.client import Sushi5Client, SushiError, SushiException
from celus_nigiri.counter4 import Counter4ReportBase
from celus_nigiri.counter5 import Counter5ReportBase, TransportError
from core.exceptions import FileConsistencyError
from django.conf import settings
from django.db.transaction import atomic
from logs.exceptions import DataStructureError
from logs.logic.data_import import create_import_batch_or_crash, import_counter_records
from logs.models import OrganizationPlatform
from sushi.models import AttemptStatus, SushiFetchAttempt

logger = logging.getLogger(__name__)


def validate_data_v5(report: Counter5ReportBase):
    Sushi5Client.validate_data(report.errors, report.warnings)


def validate_data_v4(report: Counter4ReportBase):
    # Counter 4 validation is skipped
    return None


def check_importable_attempt(attempt: SushiFetchAttempt):

    if attempt.status == AttemptStatus.SUCCESS:
        raise ValueError(f'Data already imported (attempt={attempt.pk})')

    elif attempt.status == AttemptStatus.DOWNLOAD_FAILED:
        raise ValueError(f'Trying to import data when download failed (attempt={attempt.pk})')

    elif attempt.status == AttemptStatus.NO_DATA:
        raise ValueError(f'Attempt contains no data (attempt={attempt.pk})')

    if attempt.status == AttemptStatus.IMPORT_FAILED:
        raise ValueError(f'Import of data already crashed (attempt={attempt.pk})')

    if attempt.status not in [AttemptStatus.IMPORTING, AttemptStatus.UNPROCESSED]:
        raise ValueError(f'Could not import data (attempt={attempt.pk})')


@atomic
def import_one_sushi_attempt(attempt: SushiFetchAttempt):
    # check file consistency first
    try:
        attempt.check_self_checksum()
    except FileConsistencyError as exc:
        attempt.mark_crashed(exc)
        return

    counter_version = attempt.credentials.counter_version
    reader_cls = attempt.counter_report.get_reader_class(json_format=attempt.file_is_json())
    if not reader_cls:
        logger.warning('Unsupported report type %s', attempt.counter_report.code)
        return

    check_importable_attempt(attempt)

    logger.debug('Processing file: %s; time: %.3f', attempt.data_file.name, time())

    reader = reader_cls()
    try:
        records = reader.file_to_records(os.path.join(settings.MEDIA_ROOT, attempt.data_file.name))
        logger.debug('Records parsed; time: %.3f', time())
    except FileNotFoundError as e:
        logger.error('Cannot find the referenced file - probably deleted?: %s', e)
        attempt.mark_crashed(e)
        return
    try:
        if counter_version == 4:
            validate_data_v4(reader)
        elif counter_version == 5:
            validate_data_v5(reader)
    except SushiException as e:
        # if we find validation error on data revalidation, we switch the report success attr
        logger.error('Validation error: %s', e)
        logger.info('Marking the attempt as unsuccessful')
        attempt.status = AttemptStatus.IMPORT_FAILED
        if isinstance(e.text, SushiError):
            attempt.log = str(e.text)
            attempt.error_code = e.text.code
        else:
            attempt.log = str(e)
        # fill in extracted_data
        if hasattr(reader, 'header') and type(reader.header) is dict:
            attempt.extract_header_data(reader.header)
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

    # check errors first - there are cases when partial data is returned together with
    # a SUSHI exception. We do not want to ingest such data
    if counter_version == 5 and reader.errors:
        error = reader.errors[0]
        attempt.log = '; '.join(str(e) for e in reader.errors)
        logger.warning('Found errors: %s', attempt.log)
        if isinstance(error, TransportError):
            attempt.status = AttemptStatus.DOWNLOAD_FAILED
        else:
            attempt.error_code = error.code
            attempt.status = AttemptStatus.DOWNLOAD_FAILED
        attempt.save()
    # now read the data and import it
    elif reader.record_found:
        import_batches, stats = import_counter_records(
            attempt.counter_report.report_type,
            attempt.credentials.organization,
            attempt.credentials.platform,
            records,
            months=[
                attempt.start_date.isoformat()
                if isinstance(attempt.start_date, date)
                else attempt.start_date
            ],
        )
        if len(import_batches) > 1:
            raise DataStructureError('Cannot import data for more than one month from SUSHI')
        # it is possible that because of month filter there will be no data imported anyway
        # here we handle such situation
        if import_batches:
            attempt.import_batch = import_batches[0]
            attempt.status = AttemptStatus.SUCCESS
        else:
            attempt.status = AttemptStatus.NO_DATA
            # it may be overwritten bellow with sushi warnings, but that's not a problem
            attempt.log = 'No data found during import'
        if counter_version == 5 and (reader.errors or reader.warnings):
            attempt.log = 'Warnings: {}'.format('; '.join(str(w) for w in reader.warnings))
            attempt.error_code = reader.warnings[0].code
        attempt.save()
        logger.info('Import stats: %s', stats)
    else:
        # Process errors for counter5
        if counter_version == 5 and reader.warnings:
            attempt.log = 'Warnings: {}'.format('; '.join(str(w) for w in reader.warnings))
        else:
            attempt.log = 'No data found during import'
        attempt.status = AttemptStatus.NO_DATA
        # create empty import batch each time empty data are imported
        attempt.import_batch = create_import_batch_or_crash(
            report_type=attempt.counter_report.report_type,
            organization=attempt.credentials.organization,
            platform=attempt.credentials.platform,
            month=attempt.start_date,
        )
        attempt.save()
        logger.warning('No records found!')
    # fill in extracted_data
    if hasattr(reader, 'header') and type(reader.header) is dict:
        if attempt.extract_header_data(reader.header):
            attempt.save()
    attempt.mark_processed()


def reprocess_attempt(attempt: SushiFetchAttempt) -> typing.Optional[SushiFetchAttempt]:
    if attempt.unprocess() is None:  # note: empty dict is valid output of `unprocess`
        return None
    try:
        import_one_sushi_attempt(attempt)
    except Exception as e:
        # we catch any kind of error to make sure that there is no crash
        logger.error('Importing sushi attempt #%d crashed: %s', attempt.pk, e)
        attempt.mark_crashed(e)
    return attempt
