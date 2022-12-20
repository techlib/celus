import csv

import reversion
from django.core.management import CommandError
from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from logs.models import ReportType
from publications.models import Platform
from sushi.models import CounterReportType


class Command(BaseCommand):

    help = 'Loads the combinations of platform and report types from a CSV table'

    def add_arguments(self, parser):
        parser.add_argument('file', help='input CSV file')
        parser.add_argument(
            '-4',
            dest='counter_4_col',
            default='Counter 4 - download',
            help='name of column for COUNTER 4 reports',
        )
        parser.add_argument(
            '--interest-4',
            dest='interest_4_col',
            default='Counter 4 - interest',
            help='name of column for COUNTER 4 interest reports',
        )
        parser.add_argument(
            '-5',
            dest='counter_5_col',
            default='Counter 5 - download',
            help='name of column for COUNTER 5 reports',
        )
        parser.add_argument(
            '--interest-5',
            dest='interest_5_col',
            default='Counter 5 - interest',
            help='name of column for COUNTER 5 interest reports',
        )
        parser.add_argument(
            '-p', dest='platform', default='Platform', help='name of column for Platform'
        )

    def report_list_str_to_objs(self, text: str, rt_ver_code_to_obj, counter_ver, platform_code):
        report_objs = []
        reports = [part.strip() for part in text.split(',')]
        if not reports:
            self.stderr.write(
                self.style.WARNING(
                    f'No reports defined for version {counter_ver} '
                    f'and platform "{platform_code}"'
                )
            )
        else:
            for report in reports:
                rt_obj = rt_ver_code_to_obj.get((counter_ver, report))
                if rt_obj:
                    report_objs.append(rt_obj)
                else:
                    self.stderr.write(
                        self.style.ERROR(
                            f'Unrecognized report "{report}" for version '
                            f'{counter_ver} and platform "{platform_code}"'
                        )
                    )
        return report_objs

    @atomic
    def handle(self, *args, **options):
        c4_col_name = options['counter_4_col']
        c5_col_name = options['counter_5_col']
        c4_col_interest = options['interest_4_col']
        c5_col_interest = options['interest_5_col']
        platform_col = options['platform']
        rt_ver_code_to_obj = {
            (rt.counter_version, rt.code): rt for rt in CounterReportType.objects.all()
        }
        report_type_code_to_obj = {
            (None, report_type.short_name): report_type for report_type in ReportType.objects.all()
        }
        platform_short_name_to_obj = {pl.short_name: pl for pl in Platform.objects.all()}
        platform_to_interest = {}
        with open(options['file'], 'r') as infile:
            reader = csv.DictReader(infile)
            if platform_col not in reader.fieldnames:
                raise CommandError(
                    f'File does not contain the "{platform_col}" column for '
                    f'platform or has wrong format'
                )
            if c4_col_name not in reader.fieldnames:
                self.stderr.write(
                    self.style.WARNING(f'Column "{c4_col_name}" for COUNTER 4 not present')
                )
            if c5_col_name not in reader.fieldnames:
                self.stderr.write(
                    self.style.WARNING(f'Column "{c5_col_name}" for COUNTER 5 not present')
                )
            for rec in reader:
                platform_code = rec.get(platform_col)
                if not platform_code:
                    self.stderr.write(self.style.WARNING('No platform code, skipping'))
                    continue
                platform = platform_short_name_to_obj.get(platform_code)  # type: Platform
                if not platform:
                    self.stderr.write(
                        self.style.ERROR(f'Unknown platform "{platform_code}", skipping')
                    )
                    continue
                if platform.sushicredentials_set.count() == 0:
                    self.stderr.write(
                        self.style.ERROR(
                            f'No sushi credentials for platform "{platform_code}", skipping'
                        )
                    )
                    continue
                for counter_ver, col_name, col_interest in (
                    (4, c4_col_name, c4_col_interest),
                    (5, c5_col_name, c5_col_interest),
                ):
                    rts = rec.get(col_name, '')
                    report_objs = []
                    if rts:
                        report_objs = self.report_list_str_to_objs(
                            rts, rt_ver_code_to_obj, counter_ver, platform_code
                        )
                    if report_objs:
                        sc_count = 0
                        for sc in platform.sushicredentials_set.filter(counter_version=counter_ver):
                            with reversion.create_revision():
                                sc.counter_reports.set(report_objs)
                                reversion.set_comment(
                                    'Active reports synced by load_platform_report_table command'
                                )
                            sc_count += 1
                        rep_names = ', '.join(rep.code for rep in report_objs)
                        self.stderr.write(
                            self.style.SUCCESS(
                                f'Linked reports {rep_names} to {sc_count} SUSHI credentials objects'
                            )
                        )
                    # process the interest defining reports - we collect them together and then
                    # process them at the end
                    int_rts = rec.get(col_interest, '')
                    if int_rts:
                        int_report_objs = self.report_list_str_to_objs(
                            int_rts, report_type_code_to_obj, None, platform_code
                        )
                        print(int_rts, int_report_objs)

                        if platform_code not in platform_to_interest:
                            platform_to_interest[platform_code] = []
                        platform_to_interest[platform_code] += int_report_objs

        # deal with the interest defining report types
        for platform_code, int_report_objs in platform_to_interest.items():
            if int_report_objs:
                platform = platform_short_name_to_obj[platform_code]
                platform.interest_reports.set(int_report_objs)
                self.stderr.write(
                    self.style.SUCCESS(
                        f'Linked platform {platform_code} to {len(int_report_objs)} reports '
                        f'for interest calculation'
                    )
                )
            else:
                self.stderr.write(
                    self.style.WARNING(
                        f'No known reports to add to ' f'platform {platform_code}: "{int_rts}"'
                    )
                )
