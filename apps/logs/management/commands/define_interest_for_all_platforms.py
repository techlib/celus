import logging
from collections import Counter

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from logs.models import ReportType
from publications.models import Platform, PlatformInterestReport

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Go over all platforms and assign "standard" set of interest report to all'

    def add_arguments(self, parser):
        parser.add_argument('--do-it', dest='doit', action='store_true')

    @atomic
    def handle(self, *args, **options):
        stats = Counter()
        tr_report = ReportType.objects.get(short_name='TR')
        dr_report = ReportType.objects.get(short_name='DR')
        jr1_report = ReportType.objects.get(short_name='JR1')
        br2_report = ReportType.objects.get(short_name='BR2')
        db1_report = ReportType.objects.get(short_name='DB1')
        reports = [tr_report, dr_report, jr1_report, br2_report, db1_report]
        for platform in Platform.objects.all():
            for report in reports:
                obj, created = PlatformInterestReport.objects.get_or_create(
                    platform=platform, report_type=report
                )
                if created:
                    stats['created'] += 1
                else:
                    stats['existing'] += 1
        print(stats)
        if not options['doit']:
            raise ValueError('preventing db commit, use --do-it to really do it ;)')
