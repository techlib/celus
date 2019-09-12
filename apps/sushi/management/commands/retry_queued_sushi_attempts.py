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
from sushi.logic.fetching import retry_queued
from sushi.models import SushiCredentials, CounterReportType, SushiFetchAttempt


logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Goes over the queued sushi attempts and redownloads them where needed'

    def add_arguments(self, parser):
        parser.add_argument('-n', dest='number', type=int, default=0,
                            help='number of attempts to process')

    def handle(self, *args, **options):
        retry_queued(number=options['number'])
