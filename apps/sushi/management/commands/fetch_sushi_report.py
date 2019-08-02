import logging
from datetime import date

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from sushi.models import SushiCredentials, CounterReportType

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Creates an attempt to fetch SUSHI data'

    def add_arguments(self, parser):
        parser.add_argument('-o', dest='organization', help='internal_id of the organization')
        parser.add_argument('-c', dest='version', help='COUNTER version')
        parser.add_argument('-p', dest='platform', help='short_name of the platform')
        parser.add_argument('-r', dest='report', help='code of the counter report to fetch')

    @atomic
    def handle(self, *args, **options):
        args = {}
        if options['organization']:
            args['organization__internal_id'] = options['organization']
        if options['platform']:
            args['platform__short_name'] = options['platform']
        if options['version']:
            args['counter_version'] = int(options['version'])
        credentials = SushiCredentials.objects.filter(**args)
        cr_args = {}
        if options['version']:
            cr_args['counter_version'] = int(options['version'])
        if options['report']:
            cr_args['code'] = options['report']
        crs = CounterReportType.objects.filter(**cr_args)
        # now fetch all possible combinations
        i = 0
        for cred in credentials:
            for cr in crs:
                if cr.counter_version == cred.counter_version:
                    self.stderr.write(self.style.NOTICE(f'Fetching {cred}, {cr}'))
                    attemp = cred.fetch_report(counter_report=cr,
                                               start_date=date(2019, 1, 1),
                                               end_date=date(2019, 5, 31))
                    if attemp.success:
                        style = self.style.SUCCESS
                    else:
                        style = self.style.ERROR
                    self.stderr.write(style(attemp))
                    i += 1
        if i == 0:
            self.stderr.write(self.style.WARNING('No matching reports found!'))




