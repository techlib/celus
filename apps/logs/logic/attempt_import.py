import itertools
import logging
import typing
from datetime import date
from pathlib import Path
from time import time

from celus_nigiri.client import Sushi5Client, SushiError, SushiException
from celus_nigiri.counter5 import CounterError, TransportError
from celus_nigiri.record import CounterRecord
from core.exceptions import FileConsistencyError
from django.conf import settings
from django.db.transaction import atomic
from nibbler.logic.processing import counter_format_poops, output_to_poops
from sushi.models import AttemptStatus, SushiFetchAttempt

from logs.exceptions import DataStructureError, NibblerErrors
from logs.logic.data_import import (
    create_import_batch_or_crash,
    import_counter_records,
    wipe_empty_or_partial_import_batches,
)

logger = logging.getLogger(__name__)


def validate_data_v5(errors, warnings):
    Sushi5Client.validate_data(errors, warnings)


def get_empty_records(
    records: typing.Generator[CounterRecord, None, None],
) -> typing.Tuple[bool, typing.Generator[CounterRecord, None, None]]:
    """
    Checks whether the iterator is empty

    returns: True / False, new iterator
    """
    test_empty, records = itertools.tee(records, 2)
    try:
        next(test_empty)
    except StopIteration:
        empty = True
    else:
        empty = False

    # Note that original iterator can't be used after tee()
    # so well return the new one
    return empty, records


@atomic
def import_one_sushi_attempt(attempt: SushiFetchAttempt):
    # check file consistency first
    try:
        attempt.check_self_checksum()
    except FileConsistencyError as exc:
        attempt.mark_crashed(exc)
        return
    attempt.check_importable()

    nibbler_parser = attempt.counter_report.get_nibbler_parser(json_format=attempt.file_is_json())
    path = Path(settings.MEDIA_ROOT) / attempt.data_file.name
    try:
        logger.debug("Processing file: %s; time: %.3f", attempt.data_file.name, time())
        poops = counter_format_poops(path, nibbler_parser, attempt.credentials.platform)

        # Check the output note that poops.extras should countain counter header
        poop = output_to_poops(poops)[0]
        logger.debug("Records parsed; time: %.3f", time())

        records = (e[1] for e in poop.records_basic())

    except NibblerErrors as e:
        logger.warning("Failed to parse file using nibbler", exc_info=e)
        attempt.mark_crashed(e)
        return
    except FileNotFoundError as e:
        logger.error("Cannot find the referenced file - probably deleted?: %s", e)
        attempt.mark_crashed(e)
        return

    # extract errors and warnings
    warnings = []
    errors = []
    sushi_errors = Sushi5Client.extract_errors_from_data(poop.extras)
    for sushi_error in sushi_errors:
        counter_error = CounterError.from_sushi_error(sushi_error)
        if sushi_error.is_warning:
            warnings.append(counter_error)
        elif sushi_error.is_info:
            pass
        else:
            errors.append(counter_error)

    counter_version = attempt.credentials.counter_version
    try:
        if counter_version == 5:
            # Note that only C5 is validated here
            Sushi5Client.validate_data(errors, warnings)
    except SushiException as e:
        # if we find validation error on data revalidation, we switch the report success attr
        logger.error("Validation error: %s", e)
        logger.info("Marking the attempt as unsuccessful")
        attempt.status = AttemptStatus.IMPORT_FAILED
        if isinstance(e.text, SushiError):
            attempt.log = str(e.text)
            attempt.error_code = e.text.code
        else:
            attempt.log = str(e)
        # fill in extracted_data
        if poop.extras:
            attempt.extract_header_data(poop.extras)
        attempt.save()
        return

    empty, records = get_empty_records(records)
    # check errors first - there are cases when partial data is returned together with
    # a SUSHI exception. We do not want to ingest such data
    if counter_version == 5 and errors:
        error = errors[0]
        attempt.log = "; ".join(str(e) for e in errors)
        logger.warning("Found errors: %s", attempt.log)
        if not isinstance(error, TransportError):
            attempt.error_code = error.code
        attempt.status = AttemptStatus.DOWNLOAD_FAILED
        attempt.save()
    elif not empty:
        month = (
            attempt.start_date.isoformat()
            if isinstance(attempt.start_date, date)
            else attempt.start_date
        )

        # remove empty import batches to avoid the clash during import
        if count := wipe_empty_or_partial_import_batches(
            attempt.counter_report.report_type,
            attempt.credentials.organization,
            attempt.credentials.platform,
            month,
        ):
            logger.info("%d empty conflicting ImportBatch(es) were deleted", count)

        try:
            import_batches, stats = import_counter_records(
                attempt.counter_report.report_type,
                attempt.credentials.organization,
                attempt.credentials.platform,
                records,
                months=[month],
            )
        except SushiException as e:
            logger.error("Failed to parse data due to sushi error", exc_info=e)
            attempt.mark_crashed(e)
            return
        except NibblerErrors as e:
            logger.warning(
                "Failed to parse file using nibbler while processing records", exc_info=e
            )
            attempt.mark_crashed(e)
            return

        if len(import_batches) > 1:
            raise DataStructureError("Cannot import data for more than one month from SUSHI")
        # it is possible that because of month filter there will be no data imported anyway
        # here we handle such situation
        if import_batches:
            attempt.import_batch = import_batches[0]
            attempt.status = AttemptStatus.SUCCESS
        else:
            attempt.status = AttemptStatus.NO_DATA
            # it may be overwritten bellow with sushi warnings, but that's not a problem
            attempt.log = "No data found during import"
        if counter_version == 5 and (errors or warnings):
            attempt.log = f"Warnings: {'; '.join(str(w) for w in warnings)}"
            attempt.error_code = warnings[0].code
        attempt.save()
        logger.info("Import stats: %s", stats)
    else:
        # Process errors for counter5
        if counter_version == 5 and warnings:
            attempt.log = f"Warnings: {'; '.join(str(w) for w in warnings)}"
        else:
            attempt.log = "No data found during import"
        attempt.status = AttemptStatus.NO_DATA
        # create empty import batch each time empty data are imported
        attempt.import_batch = create_import_batch_or_crash(
            report_type=attempt.counter_report.report_type,
            organization=attempt.credentials.organization,
            platform=attempt.credentials.platform,
            month=attempt.start_date,
        )
        attempt.save()
        logger.warning("No records found!")
    # fill in extracted_data
    if poop.extras and attempt.extract_header_data(poop.extras):
        attempt.save()
    attempt.mark_processed()


def reprocess_attempt(attempt: SushiFetchAttempt) -> typing.Optional[SushiFetchAttempt]:
    if attempt.reimport() is None:  # note: empty dict is valid output of `reimport`
        return None
    try:
        import_one_sushi_attempt(attempt)
    except Exception as e:
        # we catch any kind of error to make sure that there is no crash
        logger.error("Importing sushi attempt #%d crashed: %s", attempt.pk, e)
        attempt.mark_crashed(e)
    return attempt
