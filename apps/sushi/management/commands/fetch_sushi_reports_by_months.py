import concurrent.futures
from collections import namedtuple
from datetime import timedelta, date
from time import sleep
import logging

from dateparser import parse as parse_date

from django.core.management.base import BaseCommand

from core.logic.dates import month_start, month_end
from organizations.models import Organization
from publications.models import Platform
from sushi.models import SushiCredentials, CounterReportType, SushiFetchAttempt


logger = logging.getLogger(__name__)


class FetchUnit(object):

    """
    Represents one combination of platform, organization and report type which should
    start at some point in time and continue down the line to fetch older and older data
    """

    def __init__(self, credentials: SushiCredentials, report_type: CounterReportType):
        self.credentials = credentials
        self.report_type = report_type
        self.last_attempt = None

    def download(self, start_date, end_date):
        logger.info('Fetching %s, %s for %s', self.credentials, self.report_type, start_date)
        attempt = self.credentials.fetch_report(counter_report=self.report_type,
                                                start_date=start_date,
                                                end_date=end_date)
        logger.info('Result: %s', attempt)
        self.last_attempt = attempt
        return attempt

    def find_conflicting(self, start_date, end_date):
        """
        Find SushiFetch attempt corresponding to our credentials and report type and the dates
        at hand. If found, it selected the one that has the best result and returns it
        :param start_date:
        :param end_date:
        :return:
        """
        attempts = SushiFetchAttempt.objects.filter(
            credentials=self.credentials, counter_report=self.report_type, start_date=start_date,
            end_date=end_date
        )
        successes = ['contains_data', 'processing_success', 'download_success']
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


class Command(BaseCommand):

    help = 'Creates an attempt to fetch SUSHI data'
    conflict_strategies = ['continue', 'skip', 'stop']

    def add_arguments(self, parser):
        parser.add_argument('-o', dest='organization', help='internal_id of the organization')
        parser.add_argument('-p', dest='platform', help='short_name of the platform')
        parser.add_argument('-r', dest='report', help='code of the counter report to fetch')
        parser.add_argument('-s', dest='start_date')
        parser.add_argument('-e', dest='end_date', default='2018-01-01')
        parser.add_argument('--conflict-error', dest='conflict_error',
                            default='continue', choices=self.conflict_strategies)
        parser.add_argument('--conflict-ok', dest='conflict_ok',
                            default='skip', choices=self.conflict_strategies)
        parser.add_argument('--sleep', dest='sleep', type=int, default=0,
                            help='Time to sleep between requests in ms')
        parser.add_argument('-u', action='store_true', dest='skip_on_unsuccess',
                            help='do not attempt new fetching if even an unsuccessful attempt '
                                 'exists')

    def handle(self, *args, **options):
        self.sleep_time = options['sleep'] / 1000
        self.conflict_error = options['conflict_error']
        self.conflict_ok = options['conflict_ok']
        rt_args = {'active': True}
        if options['report']:
            rt_args['code'] = options['report']
        cred_args = {}
        if options['organization']:
            cred_args['organization__internal_id__startswith'] = options['organization']
        if options['platform']:
            cred_args['platform__short_name'] = options['platform']
        start_date = month_start(parse_date(options['start_date']))
        end_date = month_start(parse_date(options['end_date']))
        # prepare the fetch units - lines for which we will try to fetch data month by month
        fetch_units = []
        seen_units = set()  # org_id, plat_id, rt_id for unsuperseeded report type
        # get all credentials that are connected to a unsuperseeded report type
        for rt in CounterReportType.objects.filter(superseeded_by__isnull=True, **rt_args):
            for credentials in rt.sushicredentials_set.filter(**cred_args):
                fetch_units.append(FetchUnit(credentials, rt))
                seen_units.add((credentials.organization_id, credentials.platform_id, rt.pk))
        # go over the superseeded report types and see if we should add some
        # for example because newer version of the report type is not supported on that platform
        for rt in CounterReportType.objects.filter(superseeded_by__isnull=False, **rt_args):
            for credentials in rt.sushicredentials_set.filter(**cred_args):
                key = (credentials.organization_id, credentials.platform_id, rt.superseeded_by_id)
                if key not in seen_units:
                    fetch_units.append(FetchUnit(credentials, rt))
                    seen_units.add(key)
        # split the fetch units by platform so that we can process each platform in separate
        # thread
        platform_to_fetch_units = {}
        for fetch_unit in fetch_units:
            platform_id = fetch_unit.credentials.platform_id
            if platform_id not in platform_to_fetch_units:
                platform_to_fetch_units[platform_id] = []
            platform_to_fetch_units[platform_id].append(fetch_unit)
        # now process the fetch units
        args = [(fus, start_date, end_date) for fus in platform_to_fetch_units.values()]
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            for result in executor.map(self.process_fetch_units, args):
                pass
        # self.process_fetch_units(fetch_units, start_date, end_date)

    def decide_conflict(self, previous: SushiFetchAttempt):
        if previous.contains_data:
            return self.conflict_ok
        else:
            return self.conflict_error

    def process_fetch_units(self, args):
        fetch_units, start_date, end_date = args  # type: [FetchUnit], date, date
        while fetch_units and start_date >= end_date:
            new_fetch_units = []
            platform = fetch_units[0].credentials.platform
            self.stderr.write(self.style.NOTICE(
                f'Processing {len(fetch_units)} fetch units for platform {platform}, {start_date}')
            )
            for fetch_unit in fetch_units:  # type: FetchUnit
                end = month_end(start_date)
                # deal with possible conflict
                conflict = fetch_unit.find_conflicting(start_date, end)
                if conflict:
                    action = self.decide_conflict(conflict)
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
                attempt = fetch_unit.download(start_date, end)
                if attempt.contains_data or attempt.queued:
                    new_fetch_units.append(fetch_unit)
                else:
                    # no data in this attempt, we split or end (when split return nothing)
                    split_units = fetch_unit.split()
                    # the the new units on the same dates
                    for i, unit in enumerate(split_units):
                        if i != 0:
                            sleep(self.sleep_time)
                        attempt = unit.download(start_date, end)
                        if attempt.contains_data:
                            new_fetch_units.append(unit)
                if fetch_unit is not fetch_units[-1]:
                    sleep(self.sleep_time)
            fetch_units = new_fetch_units
            if fetch_units:
                sleep(self.sleep_time)  # we will do one more round, we need to sleep
            start_date = month_start(start_date - timedelta(days=20))
