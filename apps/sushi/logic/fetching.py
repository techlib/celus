"""
Stuff related to fetching data from SUSHI servers.
"""
import concurrent.futures
import logging
from collections import Counter
from datetime import timedelta, date
from functools import partial
from time import sleep

from django.conf import settings
from django.db.models import Count
from django.utils.timezone import now

from dateparser import parse as parse_date

from core.logic.dates import month_start, month_end
from core.task_support import cache_based_lock
from nigiri.client import SushiClientBase
from sushi.models import SushiFetchAttempt, SushiCredentials, CounterReportType

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
    qs = SushiFetchAttempt.objects.filter(queued=True, processing_success=True).\
        annotate(following_count=Count('queue_following')).filter(following_count=0).\
        order_by('-when_queued')
    logger.debug('Found %s attempts to retry', qs.count())
    last_platform = None
    stats = Counter()
    for i, attempt in enumerate(qs):
        cred_based_delay = attempt.credentials.when_can_access()
        logger.debug('Credentials based delay is %d s', cred_based_delay)
        when_retry = max(attempt.when_to_retry(), now() + timedelta(seconds=cred_based_delay))
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


def fetch_new_sushi_data():
    fetch_units = create_fetch_units()
    lock_name_to_units = split_fetch_units_by_url_lock_name(fetch_units)
    start_date = month_start(month_start(now().date()) - timedelta(days=15))  # start of prev month
    end_date = month_start(parse_date(settings.SUSHI_ATTEMPT_LAST_DATE))
    # do not use lock, we lock the whole queue with same URL
    processing_fn = partial(process_fetch_units_wrapper,
                            conflict_ok='stop', conflict_error='continue', sleep_time=2,
                            use_lock=False)
    args = [(lock_name, fus, start_date, end_date)
            for lock_name, fus in lock_name_to_units.items()]
    logger.info('Starting processing of %d sushi fetching queues', len(args))
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        for result in executor.map(processing_fn, args):
            pass


def process_fetch_units_wrapper(args, **kwargs):
    lock_name, fetch_units, start_date, end_date = args
    with cache_based_lock(lock_name):
        process_fetch_units(fetch_units, start_date, end_date, **kwargs)


class FetchUnit(object):

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
        attempt = self.credentials.fetch_report(counter_report=self.report_type,
                                                start_date=start_date,
                                                end_date=end_date,
                                                use_url_lock=use_lock)
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

    def find_conflicting(self, start_date, end_date):
        """
        Find SushiFetch attempt corresponding to our credentials and report type and the dates
        at hand. If found, it selected the one that has the best result and returns it
        :param start_date:
        :param end_date:
        :return:
        """
        attempts = SushiFetchAttempt.objects.filter(
            credentials=self.credentials, counter_report=self.report_type,
            start_date__lte=start_date, end_date__gte=end_date
        )
        successes = ['contains_data', 'queued', 'processing_success', 'download_success']
        for success_type in successes:
            matching = [attempt for attempt in attempts if getattr(attempt, success_type) is True]
            if matching:
                return matching[0]
        return attempts[0] if attempts else None

    def split(self):
        """
        If there are credentials for the same platform and organization and an older superseeded
        report type than the one associated with this object, return a list of corresponding
        FetchUnits
        """
        out = []
        for rt in self.report_type.superseeds.all():
            for cred in SushiCredentials.objects.filter(
                    active_counter_reports=rt, organization_id=self.credentials.organization_id,
                    platform_id=self.credentials.platform_id):
                out.append(FetchUnit(cred, rt))
        return out


def create_fetch_units():
    # prepare the fetch units - lines for which we will try to fetch data month by month
    fetch_units = []
    seen_units = set()  # org_id, plat_id, rt_id for unsuperseeded report type
    # get all credentials that are connected to a unsuperseeded report type
    for rt in CounterReportType.objects.filter(superseeded_by__isnull=True, active=True):
        for credentials in rt.sushicredentials_set.filter(enabled=True):
            fetch_units.append(FetchUnit(credentials, rt))
            seen_units.add((credentials.organization_id, credentials.platform_id, rt.pk))
    # go over the superseeded report types and see if we should add some
    # for example because newer version of the report type is not supported on that platform
    for rt in CounterReportType.objects.filter(superseeded_by__isnull=False, active=True):
        for credentials in rt.sushicredentials_set.filter(enabled=True):
            key = (credentials.organization_id, credentials.platform_id, rt.superseeded_by_id)
            if key not in seen_units:
                fetch_units.append(FetchUnit(credentials, rt))
                seen_units.add(key)
    return fetch_units


def split_fetch_units_by_platform(fetch_units) -> dict:
    """
    split the fetch units by platform so that we can process each platform in separate
    thread or task
    :return: platform_id -> [FetchUnit]
    """
    platform_to_fetch_units = {}
    for fetch_unit in fetch_units:
        platform_id = fetch_unit.credentials.platform_id
        if platform_id not in platform_to_fetch_units:
            platform_to_fetch_units[platform_id] = []
        platform_to_fetch_units[platform_id].append(fetch_unit)
    return platform_to_fetch_units


def split_fetch_units_by_url_lock_name(fetch_units) -> dict:
    """
    split the fetch units by platform so that we can process each platform in separate
    thread or task
    :return: url_lock_name -> [FetchUnit]
    """
    lock_name_to_fetch_units = {}
    for fetch_unit in fetch_units:
        url_lock_name = fetch_unit.credentials.url_lock_name
        if url_lock_name not in lock_name_to_fetch_units:
            lock_name_to_fetch_units[url_lock_name] = []
        lock_name_to_fetch_units[url_lock_name].append(fetch_unit)
    return lock_name_to_fetch_units


def process_fetch_units(fetch_units: [FetchUnit], start_date: date, end_date: date,
                        conflict_ok='skip', conflict_error='continue', sleep_time=0,
                        use_lock=True):
    while fetch_units and start_date >= end_date:
        new_fetch_units = []
        platform = fetch_units[0].credentials.platform
        logger.debug('Processing %d fetch units for platform %s, %s',
                     len(fetch_units), platform, start_date)
        for fetch_unit in fetch_units:  # type: FetchUnit
            end = month_end(start_date)
            # deal with possible conflict
            conflict = fetch_unit.find_conflicting(start_date, end)
            if conflict:
                action = conflict_ok if (conflict.contains_data or conflict.queued)\
                    else conflict_error
                if action == 'stop':
                    logger.debug('Skipping on existing data: %s, %s: %s',
                                 platform, fetch_unit.credentials.organization, start_date)
                    continue
                elif action == 'skip':
                    logger.debug('Skipping on existing data: %s, %s: %s',
                                 platform, fetch_unit.credentials.organization, start_date)
                    new_fetch_units.append(fetch_unit)
                    continue
                else:
                    logger.debug('Continuing regardless of existing data: %s, %s: %s',
                                 platform, fetch_unit.credentials.organization, start_date)
            # download the data
            fetch_unit.sleep()
            attempt = fetch_unit.download(start_date, end, use_lock=use_lock)
            if attempt.contains_data or attempt.queued:
                new_fetch_units.append(fetch_unit)
            else:
                # no data in this attempt, we split or end (when split return nothing)
                logger.info('Unsuccessful fetch, downgrading: %s, %s: %s',
                            platform, fetch_unit.credentials.organization, start_date)
                split_units = fetch_unit.split()
                logger.info('Downgraded %s to %s', fetch_unit.report_type.code, split_units)
                # the new units on the same dates
                for i, unit in enumerate(split_units):
                    if i != 0:
                        sleep(sleep_time)
                    unit.sleep()
                    attempt = unit.download(start_date, end, use_lock=use_lock)
                    if attempt.contains_data:
                        new_fetch_units.append(unit)
            if fetch_unit is not fetch_units[-1]:
                sleep(sleep_time)
        fetch_units = new_fetch_units
        if fetch_units:
            sleep(sleep_time)  # we will do one more round, we need to sleep
        start_date = month_start(start_date - timedelta(days=20))
