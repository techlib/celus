import json
import logging
import os
from time import time

from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from django.conf import settings

from logs.logic.materialized_interest import sync_interest_for_platform
from logs.models import ImportBatch
from nigiri.client import Sushi5Client, SushiException
from publications.models import Platform
from sushi.models import SushiFetchAttempt
from ...logic.data_import import import_counter_records
from ...models import OrganizationPlatform

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Sync interest data'

    def add_arguments(self, parser):
        parser.add_argument('-p', dest='platform', help='short name of the platform to process')

    @atomic
    def handle(self, *args, **options):
        platforms = Platform.objects.all()
        if options['platform']:
            platforms = platforms.filter(short_name=options['platform'])
        for platform in platforms:
            start = time()
            logger.info('Processing platform %s', platform)
            stats = sync_interest_for_platform(platform)
            logger.info('Duration: %s, Stats: %s', time() - start, stats)
