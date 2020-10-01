"""
Stuff related to fetching data from SUSHI servers.
"""
import concurrent.futures
import logging
import traceback
from collections import Counter, namedtuple
from datetime import timedelta, date
from functools import partial
from itertools import groupby
from time import sleep
from typing import Optional, Tuple

from dateparser import parse as parse_date
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db.models import Count
from django.utils.timezone import now

from core.logic.dates import month_start, month_end
from core.task_support import cache_based_lock
from sushi.models import (
    NO_DATA_READY_PERIOD,
    SushiFetchAttempt,
    SushiCredentials,
    CounterReportType,
)

logger = logging.getLogger(__name__)
conflict_strategies = ['continue', 'skip', 'stop']


def retry_queued(number=0, sleep_interval=0) -> Counter:
    """
    Goes over the queued SushiFetchAttempts and decides if it makes sense to redownload them.
    If yes, it does so.
    :return:
    """
    # no reason redownloading those where download was not successful - this has to be done
    # manually
    qs = (
        SushiFetchAttempt.objects.filter(queued=True, processing_success=True)
        .annotate(following_count=Count('queue_following'))
        .filter(following_count=0)
        .order_by('-when_queued')
    )
    logger.debug('Found %s attempts to retry', qs.count())
    last_platform = None
    stats = Counter()
    for i, attempt in enumerate(qs):
        cred_based_delay = attempt.credentials.when_can_access()
        logger.debug('Credentials based delay is %d s', cred_based_delay)
        attempt_retry = attempt.when_to_retry()
        if not attempt_retry:
            when_retry = None
        else:
            when_retry = max(attempt_retry, now() + timedelta(seconds=cred_based_delay))
        if when_retry and when_retry <= now():
            # we are ready to retry
            logger.debug('Retrying attempt: %s', attempt)
            new = attempt.retry()
            logger.debug('Result: %s', new)
            stats[f'retry_{new.status}'] += 1
            if attempt.credentials.platform_id == last_platform:
                sleep(sleep_interval)
            last_platform = attempt.credentials.platform_id
        else:
            # not yet time to retry
            if when_retry:
                logger.debug('Too soon to retry - need %s', when_retry - now())
                stats['too soon'] += 1
            else:
                logger.debug('Should not retry automatically')
                stats['no auto'] += 1
        if number and i >= number - 1:
            break
    return stats


def fetch_new_sushi_data(credentials: Optional[SushiCredentials] = None):
    """
    Goes over all the report types and credentials in the database and tries to fetch
    new sushi data where it makes sense
    :param credentials: if given, only report_types related to credentials organization and
                        platform will be processed
    :return:
    """
    fetch_units = create_fetch_units()
    if credentials:
        fetch_units = filter_fetch_units_by_credentials(fetch_units, credentials)
    lock_name_to_units = split_fetch_units_by_url_lock_name(fetch_units)
    start_date = month_start(
        month_start((now() - NO_DATA_READY_PERIOD).date()) - timedelta(days=15)
    )  # start of prev month
    end_date = month_start(parse_date(settings.SUSHI_ATTEMPT_LAST_DATE))
    # do not use lock, we lock the whole queue with same URL
    processing_fn = partial(
        process_fetch_units_wrapper,
        conflict_ok='skip',
        conflict_error='smart',
        sleep_time=2,
        use_lock=False,
    )
    args = [(lock_name, fus, start_date, end_date) for lock_name, fus in lock_name_to_units.items()]
    logger.info('Starting processing of %d sushi fetching queues', len(args))
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        for result in executor.map(processing_fn, args):
            pass


def process_fetch_units_wrapper(args, **kwargs):
    """
    Wrapper around `process_fetch_units` to make is simple to use it with the threading module
    """
    lock_name, fetch_units, start_date, end_date = args
    logger.debug(
        'Going to lock fetching of %d fetch units with lock %s', len(fetch_units), lock_name
    )
    with cache_based_lock(lock_name):
        logger.debug('Locked %s', lock_name)
        try:
            process_fetch_units(fetch_units, start_date, end_date, **kwargs)
        except Exception as exc:
            logger.error('Exception: %s', exc)
            logger.error('Traceback: %s', traceback.format_exc())
            raise exc
        logger.debug('Unlocked %s', lock_name)


class FetchUnit:

    """
    Represents one combination of platform, organization and report type which should
    start at some point in time and continue down the line to fetch older and older data
    """

    def __init__(self, credentials: SushiCredentials, report_type: CounterReportType):
        self.credentials = credentials
        self.report_type = report_type
        self.last_attempt = None

    def download(self, start_date, end_date, use_lock=True):
        logger.info('Fetching %s, %s for %s', self.credentials, self.report_type, start_date)
        attempt = self.credentials.fetch_report(
            counter_report=self.report_type,
            start_date=start_date,
            end_date=end_date,
            use_url_lock=use_lock,
        )
        logger.info('Result: %s', attempt)
        self.last_attempt = attempt
        return attempt

    def sleep(self):
        """
        Sleep for the time it is required for the credentials to allow new attempt
        :return:
        """
        time_to_sleep = self.credentials.when_can_access()
        if time_to_sleep:
            logger.info('Fetch unit is going to sleep for %.1f seconds', time_to_sleep)
            sleep(time_to_sleep)

    def find_conflicting(self, start_date: date, end_date: date) -> Optional[SushiFetchAttempt]:
        """
        Find SushiFetch attempt corresponding to our credentials and report type and the dates
        at hand. If found, it selects the one that has the best result and returns it
        :param start_date:
        :param end_date:
        :return:
        """
        attempts = SushiFetchAttempt.objects.filter(
            credentials=self.credentials,
            counter_report=self.report_type,
            start_date__lte=start_date,
            end_date__gte=end_date,
        ).current_or_successful(success_measure='contains_data')
        successes = ['contains_data', 'queued', 'processing_success', 'download_success']
        for success_type in successes:
            matching = [attempt for attempt in attempts if getattr(attempt, success_type) is True]
            if matching:
                return matching[0]
        return attempts[0] if attempts else None


def create_fetch_units() -> [FetchUnit]:
    """
    prepare the fetch units - lines for which we will try to fetch data month by month
    """
    # Historically, this was used to start only with C5 reports where available and
    # only downgrade to C4 if C5 was missing. However, it proved non-transparent
    # and so we decided to download all data
    fetch_units = []
    for rt in CounterReportType.objects.filter(active=True):
        for credentials in rt.sushicredentials_set.filter(enabled=True):
            fetch_units.append(FetchUnit(credentials, rt))
    return fetch_units


def filter_fetch_units_by_credentials(
    fetch_units: [FetchUnit], credentials: SushiCredentials
) -> [FetchUnit]:
    """
    Takes a list of FetchUnits and filters them so that only those that are related to
    platform and organization from `credentials` remain.
    It is used to get FetchUnits for credentials but to use credentials for newer COUNTER
    versions where desired (which naive approach based simply on `credentials` cannot do)
    """
    return [
        fu
        for fu in fetch_units
        if fu.credentials.organization_id == credentials.organization_id
        and fu.credentials.platform_id == credentials.platform_id
    ]


def split_fetch_units_by_url_lock_name(fetch_units) -> dict:
    """
    split the fetch units by the SUSHI server URL (represented by url_lock value),
    so that we can process each URL in separate thread or task and thus have control
    over timing - some SUSHI servers disallow more than one request in paralled for the
    same client, some only allow a certain number of attempts per day (and thus we need to stop
    new attempts once we detect this)
    :return: url_lock_name -> [FetchUnit]
    """
    lock_name_to_fetch_units = {}
    for fetch_unit in fetch_units:
        url_lock_name = fetch_unit.credentials.url_lock_name
        if url_lock_name not in lock_name_to_fetch_units:
            logger.debug(
                'Assigning lock name %s to URL %s', url_lock_name, fetch_unit.credentials.url
            )
            lock_name_to_fetch_units[url_lock_name] = []
        lock_name_to_fetch_units[url_lock_name].append(fetch_unit)
    return lock_name_to_fetch_units


def process_fetch_units(
    fetch_units: [FetchUnit],
    start_date: date,
    end_date: date,
    conflict_ok='skip',
    conflict_error='smart',
    sleep_time=0,
    use_lock=True,
):
    """

    :param fetch_units:
    :param start_date:
    :param end_date:
    :param conflict_ok:
    :param conflict_error:
    :param sleep_time:
    :param use_lock:
    :return:
    """
    while fetch_units and start_date >= end_date:
        new_fetch_units = []
        platform = fetch_units[0].credentials.platform
        logger.debug(
            'Processing %d fetch units for platform %s, %s', len(fetch_units), platform, start_date
        )
        for fetch_unit in fetch_units:  # type: FetchUnit
            end = month_end(start_date)
            # deal with possible conflict
            conflict = fetch_unit.find_conflicting(start_date, end)
            if conflict:
                action = (
                    conflict_ok if (conflict.contains_data or conflict.queued) else conflict_error
                )
                if action == 'smart':
                    # smart means that we use the retry timeout of the conflicting attempt
                    # to decide on what to do
                    action = smart_decide_conflict_action(conflict)
                if action == 'stop':
                    logger.debug(
                        'Stopping on existing data: %s, %s: %s',
                        platform,
                        fetch_unit.credentials.organization,
                        start_date,
                    )
                    continue
                elif action == 'skip':
                    logger.debug(
                        'Skipping on existing data: %s, %s: %s',
                        platform,
                        fetch_unit.credentials.organization,
                        start_date,
                    )
                    new_fetch_units.append(fetch_unit)
                    continue
                else:
                    logger.debug(
                        'Continuing regardless of existing data: %s, %s: %s',
                        platform,
                        fetch_unit.credentials.organization,
                        start_date,
                    )
            # download the data
            fetch_unit.sleep()
            attempt = fetch_unit.download(start_date, end, use_lock=use_lock)
            if attempt.contains_data or attempt.queued:
                new_fetch_units.append(fetch_unit)
            else:
                go_on = False
                # no data in this attempt, we must analyze it further
                if attempt.error_code:
                    error_meaning = attempt.error_explanation()
                    if error_meaning.setup_ok:
                        # this means we can process - the credentials, etc. are OK
                        go_on = True
                if go_on:
                    new_fetch_units.append(fetch_unit)
                else:
                    logger.info(
                        'Unsuccessful fetch, stoping: %s, %s: %s',
                        platform,
                        fetch_unit.credentials.organization,
                        start_date,
                    )
            # sleep but only if this is not the last in the list - it would not make sense
            # to wait just before finishing
            if fetch_unit is not fetch_units[-1]:
                sleep(sleep_time)
        fetch_units = new_fetch_units
        if fetch_units:
            sleep(sleep_time)  # we will do one more round, we need to sleep
        start_date = month_start(start_date - timedelta(days=20))
    logger.debug('Finished processing')


def smart_decide_conflict_action(conflict):
    when_retry = conflict.when_to_retry()
    if not when_retry:
        action = 'skip'  # there should be no retry
        logger.debug('Smart deciding to skip attempt - retry makes no sense')
    elif when_retry <= now():
        action = 'continue'  # it is time to retry
        logger.debug('Smart deciding to retry attempt')
    else:
        action = 'skip'  # it is too soon to retry
        logger.debug('Smart deciding to skip attempt - it is too soon to retry')
    return action


def months_to_cover(first_month=None) -> [date]:
    """
    List of dates (month starts) for which we should try to get data
    """
    last_month = month_start(month_start(now().date()) - timedelta(days=15))
    first_month = first_month or parse_date(settings.SUSHI_ATTEMPT_LAST_DATE + '-01').date()
    month = first_month
    months_to_check = []
    while month <= last_month:
        months_to_check.append(month)
        month = month_start(month + relativedelta(months=1))
    return months_to_check


DataHole = namedtuple(
    'DataHole',
    ['date', 'credentials', 'counter_report', 'attempt_count', 'attempt_with_current_credentials'],
)


def find_holes_in_data() -> [DataHole]:
    """
    Looks for months for which there should be data, but are not. The result is bound to specific
    credentials and report type
    :return:
    """
    months = months_to_cover()
    result = []
    for credentials in SushiCredentials.objects.filter(enabled=True):  # type: SushiCredentials
        for report_type in credentials.counter_reports.all():
            attempts = SushiFetchAttempt.objects.filter(
                credentials=credentials, counter_report=report_type
            )
            month_to_attempts = {
                key: list(group) for key, group in groupby(attempts, lambda x: x.start_date)
            }
            for month in months:
                attempts = month_to_attempts.get(month, [])
                # we consider queued attempts successful because they will be tried again
                # that is, holes with queued attempts are not holes :)
                successful_attempts = [
                    attempt for attempt in attempts if attempt.processing_success or attempt.queued
                ]
                # attempts with the current version of credentials
                current_attempts = [
                    attempt
                    for attempt in attempts
                    if attempt.credentials_version_hash == credentials.version_hash
                ]
                if not successful_attempts:
                    result.append(
                        DataHole(
                            date=month,
                            credentials=credentials,
                            counter_report=report_type,
                            attempt_count=len(attempts),
                            attempt_with_current_credentials=bool(current_attempts),
                        )
                    )
    return result


def retry_holes_with_new_credentials(sleep_interval=0) -> Counter:
    """
    Find holes in data using `find_holes_in_data` and decide if it makes sense to redownload them.
    If yes, do so.
    :return:
    """
    holes = find_holes_in_data()
    logger.debug('Found %d holes to retry', len(holes))
    last_platform = None
    stats = Counter()
    for hole in holes:  # type: DataHole
        cred_based_delay = hole.credentials.when_can_access()
        if not hole.attempt_with_current_credentials:
            # this is what we want to process - cases when sushi credentials were updated
            if cred_based_delay == 0:
                # we are ready to retry
                logger.debug('Trying to fill hole: %s / %s', hole.credentials, hole.date)
                attempt = hole.credentials.fetch_report(
                    counter_report=hole.counter_report,
                    start_date=hole.date,
                    end_date=month_end(hole.date),
                    use_url_lock=True,
                )
                logger.debug('Result: %s', attempt)
                stats[f'retry_{attempt.status}'] += 1
                if attempt.credentials.platform_id == last_platform:
                    sleep(sleep_interval)
                last_platform = attempt.credentials.platform_id
            else:
                logger.debug('Too soon to retry - need %d s', cred_based_delay)
                stats['too soon'] += 1
    return stats
