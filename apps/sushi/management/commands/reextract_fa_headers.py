from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from sushi.logic.cleanup import fetch_attempt_fill_in_missing_header_data


class Command(BaseCommand):

    help = 'Fill in missing header data in FetchAttempts'

    def add_arguments(self, parser):
        parser.add_argument('--do-it', dest='doit', action='store_true')

    @atomic
    def handle(self, *args, **options):
        fetch_attempt_fill_in_missing_header_data()

        if not options['doit']:
            raise ValueError('preventing db commit, use --do-it to really do it ;)')
