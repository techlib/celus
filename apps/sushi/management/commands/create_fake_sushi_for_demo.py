import logging
from collections import Counter
from uuid import uuid4

from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from django.db.transaction import atomic
from organizations.models import Organization
from publications.models import Platform
from sushi.models import CounterReportsToCredentials, CounterReportType, SushiCredentials

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = (
        'Goes over all platforms and if there is no C5 SUSHI registered for it, create one'
        'with fake sashimi server.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--do-it', dest='do_it', action='store_true', help='really do it')

    @atomic
    def handle(self, *args, **options):
        stats = Counter()
        for organization in Organization.objects.all():
            for platform in Platform.objects.annotate(
                sushi_count=Count(
                    'sushicredentials',
                    filter=Q(
                        sushicredentials__counter_version=5,
                        sushicredentials__organization=organization,
                    ),
                )
            ).filter(sushi_count=0):
                creds = SushiCredentials.objects.create(
                    platform=platform,
                    organization=organization,
                    counter_version=5,
                    url='https://demo.celus.net/sashimi/',
                    customer_id=str(uuid4()),
                    requestor_id=str(uuid4()),
                )
                stats['created'] += 1
                for code in ('TR', 'DR'):
                    counter_report = CounterReportType.objects.get(code=code)
                    CounterReportsToCredentials.objects.create(
                        credentials=creds, counter_report=counter_report
                    )
        print("Stats:", stats)
        if not options['do_it']:
            raise ValueError(
                'Raising exception to revert transaction. If you really mean it, use --do-it'
            )
