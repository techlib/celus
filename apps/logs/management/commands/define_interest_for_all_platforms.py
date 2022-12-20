import logging
from collections import Counter

from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from publications.models import Platform

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Go over all platforms and assign "standard" set of interest report to all'

    def add_arguments(self, parser):
        parser.add_argument('--do-it', dest='doit', action='store_true')

    @atomic
    def handle(self, *args, **options):
        stats = Counter()
        for platform in Platform.objects.all():
            stats += platform.create_default_interests()
        print(stats)
        if not options['doit']:
            raise ValueError('preventing db commit, use --do-it to really do it ;)')
