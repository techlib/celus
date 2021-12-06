import diskcache
import logging
import sys
import tempfile
import time

from collections import Counter
from pathlib import Path


from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from sushi.models import SushiFetchAttempt

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = (
        'Checks directory were dowloaded files from sushi are downloaded '
        'and removes files which are not associated with any attempt.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--do-it', dest='doit', action='store_true')
        parser.add_argument(
            '--older-than',
            help='Remove only files which are older that X days (default=30)',
            type=int,
            default="30",
        )

    def handle(self, *args, **options):

        if options["older_than"] < 1:
            raise CommandError("Deleted files should be at least one day old", returncode=1)
        time_limit = time.time() - options["older_than"] * 24 * 60 * 60

        stats = Counter()
        dirs = set()  # Note: We assume here that directory list will fit into memory
        with tempfile.TemporaryDirectory(prefix="celus") as tmp:
            cache = diskcache.Cache(tmp)
            for attempt in SushiFetchAttempt.objects.filter(data_file__isnull=False).exclude(
                data_file__exact=""
            ):
                filepath = Path(settings.MEDIA_ROOT) / attempt.data_file.name
                if filepath.exists():
                    stats["existing_attempt_files"] += 1
                else:
                    stats['missing_attempt_files'] += 1
                    continue

                cache.add(str(filepath), "1", expire=None)  # never expires

                parent = filepath.parent
                if parent not in dirs:
                    stats['dirs'] += 1

                dirs.add(parent)

            dirs_len = len(dirs)
            print()
            for (idx, dir_path) in enumerate(dirs):
                sys.stdout.write(f"\rCleaning dirs {idx + 1}/{dirs_len}")

                for entry in dir_path.iterdir():
                    if entry.is_file() and entry.stat().st_mtime < time_limit:
                        if cache.get(str(entry), "0") == "0":
                            stats['deleted_orphan_files'] += 1
                            if options["doit"]:
                                entry.unlink()
            print("\n")

        print(stats)
        if not options["doit"]:
            print("Files were really not deleted. --do-it to really do it ;)")
