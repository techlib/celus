import logging
from datetime import date

from dateparser import parse as parse_date

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from sushi.models import SushiCredentials, CounterReportType, SushiFetchAttempt

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Creates an attempt to fetch SUSHI data'

    def add_arguments(self, parser):
        parser.add_argument('-o', dest='organization', help='internal_id of the organization')
        parser.add_argument('-c', dest='version', help='COUNTER version')
        parser.add_argument('-p', dest='platform', help='short_name of the platform')
        parser.add_argument('-r', dest='report', help='code of the counter report to fetch')
        parser.add_argument('-s', dest='start_date', default='2019-01-01')
        parser.add_argument('-e', dest='end_date', default='2019-06-30')

    def handle(self, *args, **options):
        args = {}
        if options['organization']:
            args['organization__internal_id'] = options['organization']
        if options['platform']:
            args['platform__short_name'] = options['platform']
        if options['version']:
            args['counter_version'] = int(options['version'])
        credentials = SushiCredentials.objects.filter(**args)
        cr_args = {'active': True}
        if options['version']:
            cr_args['counter_version'] = int(options['version'])
        if options['report']:
            cr_args['code'] = options['report']
        crs = CounterReportType.objects.filter(**cr_args)
        # now fetch all possible combinations
        i = 0
        start_date = parse_date(options['start_date'])
        end_date = parse_date(options['end_date'])
        for cred in credentials:
            for cr in crs:
                if cr.counter_version == cred.counter_version:
                    # check if we have a successful attempt already and skip it if yes
                    if SushiFetchAttempt.objects.filter(
                            credentials=cred,
                            counter_report=cr,
                            start_date=start_date,
                            end_date=end_date,
                            success=True).exists():
                        self.stderr.write(self.style.SUCCESS(f'Skipping existing {cred}, {cr}'))
                    else:
                        self.stderr.write(self.style.NOTICE(f'Fetching {cred}, {cr}'))
                        attemp = cred.fetch_report(counter_report=cr,
                                                   start_date=start_date,
                                                   end_date=end_date)
                        if attemp.success:
                            style = self.style.SUCCESS
                        else:
                            style = self.style.ERROR
                        self.stderr.write(style(attemp))
                    i += 1
        if i == 0:
            self.stderr.write(self.style.WARNING('No matching reports found!'))




