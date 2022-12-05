import logging
import typing

from collections import Counter

from datetime import timedelta

from django.utils import timezone
from django.db.models import Max

from sushi.models import SushiFetchAttempt, AttemptStatus

logger = logging.getLogger(__name__)


UNSUCCESFUL_CLEANUP_PERIOD = timedelta(days=45)  # in days
CHUNK_SIZE = 2000


def cleanup_fetch_attempts_with_no_data(
    age: timedelta = UNSUCCESFUL_CLEANUP_PERIOD,
    error_code: typing.Optional[str] = None,
    organization_id: typing.Optional[int] = None,
    platform_id: typing.Optional[int] = None,
    counter_report_id: typing.Optional[int] = None,
) -> Counter:
    """ Cleans unsuccessful FetchAttempts
    """
    fltr = {
        "import_batch__isnull": True,
        "status__in": list(AttemptStatus.errors()) + [AttemptStatus.NO_DATA],
        "timestamp__lt": timezone.now() - age,
    }

    logger.info("Performing cleanup for FetchAttempts (older than %s)", age)

    latest_filter = {}

    if error_code:
        fltr["error_code"] = error_code
        latest_filter["error_code"] = error_code

    if organization_id:
        fltr["credentials__organization_id"] = organization_id
        latest_filter["credentials__organization_id"] = organization_id

    if platform_id:
        fltr["credentials__platform_id"] = platform_id
        latest_filter["credentials__platform_id"] = platform_id

    if counter_report_id:
        fltr["counter_report_id"] = counter_report_id
        latest_filter["counter_report_id"] = counter_report_id

    counter = Counter()
    logger.info("Collecting latest FetchAttempts")
    latest = (
        SushiFetchAttempt.objects.values(
            "start_date", "end_date", "counter_report_id", "credentials_id",
        )
        .annotate(latest=Max('timestamp'))
        .values_list('start_date', 'end_date', 'counter_report_id', 'credentials_id', 'latest',)
    )
    latest = {(e[0], e[1], e[2], e[3]): e[4] for e in latest}

    pks_to_delete = []
    delete_counter = 0
    logger.info("Starting to delete FetchAttempts")
    for pk, start_date, end_date, counter_report_id, credentials_id, timestamp in (
        SushiFetchAttempt.objects.filter(**fltr)
        .values_list(
            "pk", "start_date", "end_date", "counter_report_id", "credentials_id", "timestamp"
        )
        .iterator(CHUNK_SIZE)
    ):
        # check whether newer exists
        if latest[start_date, end_date, counter_report_id, credentials_id] > timestamp:
            counter["deleted"] += 1
            pks_to_delete.append(pk)
        else:
            counter["latest"] += 1

        if pks_to_delete and len(pks_to_delete) % CHUNK_SIZE == 0:
            SushiFetchAttempt.objects.filter(pk__in=pks_to_delete).delete()
            delete_counter += len(pks_to_delete)
            logger.info("%s FetchAttempts deleted", delete_counter)
            pks_to_delete = []

    if pks_to_delete:
        delete_counter += len(pks_to_delete)
        SushiFetchAttempt.objects.filter(pk__in=pks_to_delete).delete()
        logger.info("%s FetchAttempts deleted", delete_counter)

    return counter


def fetch_attempt_fill_in_missing_header_data():
    """
    Re-processes headers of all fetch attempts which are missing `extracted_data` and fills the
    data in.
    """
    stats = Counter()
    attempts = SushiFetchAttempt.objects.filter(
        extracted_data={}, counter_report__counter_version=5, data_file__isnull=False
    )
    logger.debug('Found %s attempts to process', attempts.count())
    for attempt in attempts:
        try:
            success = attempt.reextract_header_data()
        except Exception as e:
            logger.warning('Error: %s', e)
            stats[e.__class__.__name__] += 1
        else:
            state = 'success' if success else 'failure'
            stats[state] += 1
        finally:
            attempt.data_file.close()

    logger.debug('Stats: %s', stats)
