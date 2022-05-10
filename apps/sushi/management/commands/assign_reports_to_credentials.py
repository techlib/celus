import csv
import logging
from collections import Counter

import reversion
from django.core.management import CommandError

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from logs.models import ReportType
from publications.models import Platform
from sushi.models import CounterReportType, SushiCredentials


logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = (
        'Assigns a standard set of reports to credentials. If knowledgebase is available, it '
        'uses report from there, otherwise uses a standard set. ONLY WORKS FOR C5 FOR NOW!'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '-k',
            '--knowledgebase-only',
            dest='k_only',
            action='store_true',
            help='When given, nothing is assigned unless there is a knowledgebase record',
        )
        parser.add_argument(
            '-d',
            '--default',
            dest='default',
            default='TR,DR,PR',
            help='Default reports when knowledgebase is not given - separated by comma (,)',
        )
        parser.add_argument('--do-it', dest='doit', action='store_true')

    @atomic
    def handle(self, *args, **options):
        stats = Counter()
        report_types = {rt.code: rt for rt in CounterReportType.objects.all()}
        for cr in SushiCredentials.objects.filter(
            counter_reports__isnull=True, counter_version=5
        ).select_related('platform'):
            kb = cr.platform.knowledgebase or {}
            for provider in kb.get('providers', []):
                if provider.get('counter_version') == cr.counter_version:
                    to_assign = []
                    for rt_rec in provider.get('assigned_report_types', []):
                        rt_name = rt_rec.get('report_type')
                        rt = report_types.get(rt_name)
                        if rt:
                            to_assign.append(rt)
                        else:
                            logger.warning(
                                f'Unknown RT "{rt_name}" for platform "{cr.platform}" '
                                f'#{cr.platform_id}'
                            )
                    if to_assign:
                        cr.counter_reports.set(to_assign)
                        stats['knowledgebase'] += 1
                        break
            else:
                if not options['k_only']:
                    stats['default'] += 1
                    default = [report_types[code.strip()] for code in options['default'].split(',')]
                    cr.counter_reports.set(default)
                else:
                    stats['skipped no knowledgebase'] += 1
        logger.info('Stats: %s', stats)
        if not options['doit']:
            raise ValueError('preventing db commit, use --do-it to really do it ;)')
