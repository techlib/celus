import logging

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from sushi.logic import cleanup


class Command(BaseCommand):

    help = 'Cleanup old fetch attempts'

    def add_arguments(self, parser):
        parser.add_argument('--do-it', dest='doit', action='store_true')
        parser.add_argument('-o', dest='organization_id', type=int, help='Organization ID')
        parser.add_argument('-p', dest='platform_id', type=int, help='Platform ID')
        parser.add_argument('-c', dest='counter_report_id', type=int, help='Counter Report ID')
        parser.add_argument(
            '-a',
            dest='age',
            type=lambda x: timedelta(days=int(x)),
            help='How old FetchAttempts should be deleted (in days)',
            default=cleanup.UNSUCCESFUL_CLEANUP_PERIOD,
        )
        parser.add_argument(
            '-e',
            dest='error_code',
            type=lambda x: timedelta(days=int(x)),
            help='Delete FetchAttempts only with given error code',
        )

    @atomic
    def handle(self, *args, **options):
        print(
            cleanup.cleanup_fetch_attempts_with_no_data(
                age=options.get("age"),
                error_code=options.get("error_code"),
                organization_id=options.get("organization_id"),
                platform_id=options.get("platform_id"),
                counter_report_id=options.get("counter_report_id"),
            )
        )
        if not options['doit']:
            raise ValueError('preventing db commit, use --do-it to really do it ;)')
