import concurrent.futures
from time import sleep

from dateparser import parse as parse_date

from django.core.management.base import BaseCommand

from core.logic.dates import month_start, month_end
from sushi.models import SushiCredentials, CounterReportType, SushiFetchAttempt


class Command(BaseCommand):

    help = 'Creates an attempt to fetch SUSHI data'

    def add_arguments(self, parser):
        parser.add_argument('-o', dest='organization', help='internal_id of the organization')
        parser.add_argument('-c', dest='version', help='COUNTER version')
        parser.add_argument('-p', dest='platform', help='short_name of the platform')
        parser.add_argument('-r', dest='report', help='code of the counter report to fetch')
        parser.add_argument('-s', dest='start_date', default='2019-01-01')
        parser.add_argument('-e', dest='end_date', default='2019-06-30')
        parser.add_argument(
            '--sleep',
            dest='sleep',
            type=int,
            default=0,
            help='Time to sleep between requests in ms',
        )
        parser.add_argument(
            '-u',
            action='store_true',
            dest='skip_on_unsuccess',
            help='do not attempt new fetching if even an unsuccessful attempt ' 'exists',
        )

    def handle(self, *args, **options):
        self.sleep_time = options['sleep'] / 1000
        args = {}
        if options['organization']:
            args['organization__internal_id'] = options['organization']
        if options['platform']:
            args['platform__short_name'] = options['platform']
        if options['version']:
            args['counter_version'] = int(options['version'])
        credentials = list(SushiCredentials.objects.filter(**args))
        cr_args = {'active': True}
        if options['version']:
            cr_args['counter_version'] = int(options['version'])
        if options['report']:
            cr_args['code'] = options['report']
        # now fetch all possible combinations
        start_date = month_start(parse_date(options['start_date']))
        end_date = month_end(parse_date(options['end_date']))
        # we divide the requests to groups by platform and counter version combination
        # and then process each group in a separate thread
        platform_counter_v_to_requests = {}
        for cred in credentials:
            crs = list(cred.active_counter_reports.filter(**cr_args))
            for cr in crs:
                key = (cred.platform_id, cred.counter_version)
                # check if we have a successful attempt already and skip it if yes
                success_req_for_skip = (
                    {'download_success': True, 'processing_success': True}
                    if not options['skip_on_unsuccess']
                    else {}
                )
                existing = SushiFetchAttempt.objects.filter(
                    credentials=cred,
                    counter_report=cr,
                    start_date=start_date,
                    end_date=end_date,
                    **success_req_for_skip,
                ).exists()
                if existing:
                    self.stderr.write(self.style.SUCCESS(f'Skipping existing {cred}, {cr}'))
                else:
                    if key not in platform_counter_v_to_requests:
                        platform_counter_v_to_requests[key] = []
                    platform_counter_v_to_requests[key].append((cred, cr, start_date, end_date))
        if not platform_counter_v_to_requests:
            self.stderr.write(self.style.WARNING('No matching reports found!'))
            return
        # let's create some threads and use them to process individual platforms
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            for result in executor.map(
                self.download_list, list(platform_counter_v_to_requests.items())
            ):
                pass

    def download_list(self, attrs):
        key, param_list = attrs  # unpack the tuple passed in
        self.stderr.write(
            self.style.SUCCESS(f'Starting thread for {len(param_list)} downloads for key {key}')
        )
        for i, params in enumerate(param_list):
            self.download(*params)
            if i != len(param_list) - 1:
                # do not sleep for last item
                sleep(self.sleep_time)
        self.stderr.write(
            self.style.SUCCESS(f'Ending thread for {len(param_list)} downloads for key {key}')
        )

    def download(self, cred: SushiCredentials, cr: CounterReportType, start_date, end_date):
        self.stderr.write(self.style.NOTICE(f'Fetching {cred}, {cr}'))
        attempt = cred.fetch_report(counter_report=cr, start_date=start_date, end_date=end_date)
        if attempt.download_success:
            style = self.style.SUCCESS
        else:
            style = self.style.ERROR
        self.stderr.write(style(attempt))
