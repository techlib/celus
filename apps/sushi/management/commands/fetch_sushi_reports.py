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
        parser.add_argument('--sleep', dest='sleep', type=int, default=0,
                            help='Time to sleep between requests in ms')

    def handle(self, *args, **options):
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
        i = 0
        start_date = month_start(parse_date(options['start_date']))
        end_date = month_end(parse_date(options['end_date']))
        last_platform_id = None
        for cred in credentials:
            crs = list(cred.active_counter_reports.filter(**cr_args))
            for cr in crs:
                # check if we have a successful attempt already and skip it if yes
                existing = SushiFetchAttempt.objects.filter(
                        credentials=cred,
                        counter_report=cr,
                        start_date=start_date,
                        end_date=end_date,
                        download_success=True,
                        processing_success=True,
                    ).exists()

                if existing:
                    self.stderr.write(self.style.SUCCESS(f'Skipping existing {cred}, {cr}'))
                else:
                    self.stderr.write(self.style.NOTICE(f'Fetching {cred}, {cr}'))
                    attempt = cred.fetch_report(counter_report=cr,
                                                start_date=start_date,
                                                end_date=end_date)
                    if attempt.download_success:
                        style = self.style.SUCCESS
                    else:
                        style = self.style.ERROR
                    self.stderr.write(style(attempt))
                    if cred.platform_id == last_platform_id:
                        # do not sleep after the last fetch
                        sleep(options['sleep'] / 1000)
                    last_platform_id = cred.platform_id

                i += 1
        if i == 0:
            self.stderr.write(self.style.WARNING('No matching reports found!'))


