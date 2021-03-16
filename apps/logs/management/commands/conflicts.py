import logging

from django.core.management.base import BaseCommand
from django.db import connection

from logs.logic import conflicts

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Deals with data conflicts'

    def add_arguments(self, parser):
        parser.add_argument('-o', dest='organization_id', type=int, help='Organization ID')
        parser.add_argument('-p', dest='platform_id', type=int, help='Platform ID')
        parser.add_argument('-r', dest='report_type_id', type=int, help='Report Type ID')

        pass

    def handle(self, *args, **options):
        conflicts.print_conflicts(
            options["organization_id"], options["platform_id"], options["report_type_id"],
        )
        print('Queries:', len(connection.queries))
