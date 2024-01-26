import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from logs.logic.cleanup import find_split_accesslogs_with_the_same_title

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Finds records where due to title merging, accesslogs with the same key are present more "
        "than once in the database. When --fix-it is used, the records are merged together."
    )

    def add_arguments(self, parser):
        parser.add_argument("--fix-it", action="store_true", help="Actually fix the records")

    def handle(self, *args, **options):
        # first make sure we don't get too much logging
        for logger_name in ["hcube", "clickhouse_driver"]:
            logging.getLogger(logger_name).setLevel(logging.WARNING)

        if not settings.CLICKHOUSE_QUERY_ACTIVE:
            raise CommandError(
                "This command only works with clickhouse, it would be unbelievably slow otherwise"
            )

        stats = find_split_accesslogs_with_the_same_title(options["fix_it"])
        print("Stats:", stats)
