import itertools
import logging
import typing
from datetime import date

from celus_nigiri.client import Sushi5Client, Sushi51Client, SushiError, SushiException
from celus_nigiri.counter5 import CounterError, TransportError
from celus_nigiri.record import CounterRecord
from core.exceptions import FileConsistencyError
from django.db.transaction import atomic
from organizations.models import Organization
from publications.models import Platform
from sushi.models import (
    AttemptStatus,
    CounterReportsToCredentials,
    CounterVersionChoices,
    SushiCredentials,
    SushiFetchAttempt,
)

from logs.exceptions import DataStructureError, NibblerErrors, ReportDataValidityError
from logs.logic.interest.computation import sync_interest_for_import_batch

logger = logging.getLogger(__name__)


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
def import_one_sushi_attempt(
    attempt: SushiFetchAttempt,
    counter_version: typing.Optional[int] = None,
    organization: typing.Optional[Organization] = None,
    platform: typing.Optional[Platform] = None,
):
    """
    When `counter_version`, `organization` and `platform` are provided, they override the
    credentials of the attempt. This can only be used when the attempt does not have credentials.
    (result of deletion of credentials without removal of the data)
    """
    from logs.logic.data_import import (  # noqa - slow import
        create_import_batch_or_crash,
        import_counter_records,
        wipe_empty_or_partial_import_batches,
    )

    if attempt.credentials is None:
        if counter_version is None or organization is None or platform is None:
            raise ValueError(
                "counter_version, organization and platform must be provided when the attempt does "
                "not have credentials"
            )
    else:
        if counter_version is not None or organization is not None or platform is not None:
            raise ValueError(
                "counter_version, organization and platform must not be provided when the attempt "
                "has credentials"
            )
        counter_version = attempt.credentials.counter_version
        organization = attempt.credentials.organization
        platform = attempt.credentials.platform

    # check file consistency first
    try:
        attempt.check_self_checksum()
    except FileConsistencyError as exc:
        attempt.mark_crashed(exc)
        return
    attempt.check_importable()

    try:
        poop = attempt.get_nibbler_poop(platform=platform)
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

    try:
        # Note that only C5X is validated here
        if counter_version == 5:
            Sushi5Client.validate_data(errors, warnings)
        elif counter_version == 51:
            Sushi51Client.validate_data(errors, warnings)
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
        attempt.save()
        return

    empty, records = get_empty_records(records)
    # check errors first - there are cases when partial data is returned together with
    # a SUSHI exception. We do not want to ingest such data
    if CounterVersionChoices.is_c5x(counter_version) and errors:
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
            attempt.counter_report.report_type, organization, platform, month
        ):
            logger.info("%d empty conflicting ImportBatch(es) were deleted", count)

        try:
            import_batches, stats = import_counter_records(
                attempt.counter_report.report_type, organization, platform, records, months=[month]
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
        except ReportDataValidityError as e:
            logger.error("Data validity error - marking report as broken: '%s'", e)
            attempt.mark_crashed(e)
            # mark the report as broken for the credentials
            if attempt.credentials:
                try:
                    cr2c = CounterReportsToCredentials.objects.get(
                        credentials=attempt.credentials, counter_report=attempt.counter_report
                    )
                    cr2c.set_broken(attempt, SushiCredentials.BROKEN_SUSHI)
                except CounterReportsToCredentials.DoesNotExist:
                    # Counter report was removed from credentials - we can ignore this
                    pass
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
        if CounterVersionChoices.is_c5x(counter_version) and (errors or warnings):
            attempt.log = f"Warnings: {'; '.join(str(w) for w in warnings)}"
            attempt.error_code = warnings[0].code
        attempt.save()
        logger.info("Import stats: %s", stats)
    else:
        # Process empty data
        if CounterVersionChoices.is_c5x(counter_version) and warnings:
            attempt.log = f"Warnings: {'; '.join(str(w) for w in warnings)}"
        else:
            attempt.log = "No data found during import"
        attempt.status = AttemptStatus.NO_DATA
        # create empty import batch each time empty data are imported
        attempt.import_batch = create_import_batch_or_crash(
            report_type=attempt.counter_report.report_type,
            organization=organization,
            platform=platform,
            month=attempt.start_date,
        )
        attempt.save()
        sync_interest_for_import_batch(attempt.import_batch)
        logger.warning("No records found!")
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
