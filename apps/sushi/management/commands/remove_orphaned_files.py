import logging
import os
import time
from collections import Counter
from pathlib import Path

from core.logic.debug import log_memory
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from sushi.models import SushiFetchAttempt

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Checks directory were dowloaded files from sushi are downloaded "
        "and removes files which are not associated with any attempt."
    )

    def add_arguments(self, parser):
        parser.add_argument("--do-it", dest="doit", action="store_true")
        parser.add_argument(
            "--older-than",
            help="Remove only files which are older that X days (default=30)",
            type=int,
            default="30",
        )
        parser.add_argument(
            "-p", "--print-deleted", action="store_true", help="Print deleted files"
        )

    def handle(self, *args, **options):
        if options["older_than"] < 1:
            raise CommandError("Deleted files should be at least one day old", returncode=1)
        time_limit = time.time() - options["older_than"] * 24 * 60 * 60

        stats = Counter()
        deleted_size = 0
        cache = set()

        for filename in (
            SushiFetchAttempt.objects.filter(data_file__isnull=False)
            .exclude(data_file__exact="")
            .values_list("data_file", flat=True)
        ):
            filepath = Path(settings.MEDIA_ROOT) / filename
            if filepath.exists():
                stats["existing_attempt_files"] += 1
            else:
                stats["missing_attempt_files"] += 1
                continue

            cache.add(str(filepath))

        log_memory("Before cleaning dirs")
        counter_root = Path(settings.MEDIA_ROOT) / "counter"
        for root, _dirnames, filenames in os.walk(str(counter_root)):
            for filename in filenames:
                fullpath = Path(root) / filename
                if (
                    fullpath.is_file()
                    and fullpath.stat().st_mtime < time_limit
                    and str(fullpath) not in cache
                ):
                    stats["deleted_orphan_files"] += 1
                    deleted_size += fullpath.stat().st_size
                    if options["doit"]:
                        fullpath.unlink()
                    if options["print_deleted"]:
                        print(fullpath)

        logger.info("Stats: %s", stats)
        logger.info("Deleted size: %.2f MB", deleted_size / 1024 / 1024)
        if not options["doit"]:
            logger.warning("Files were really not deleted. --do-it to really do it ;)")
