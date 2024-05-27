import logging
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from logs.cubes import AccessLogCube, ch_backend
from logs.logic.clickhouse import sync_accesslogs_with_clickhouse_superfast

from publications.logic.title_management import find_mergeable_titles, merge_titles

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Go over all titles and merge those which represent the same title"
    journal_file = Path("merge_titles.journal")

    def add_arguments(self, parser):
        parser.add_argument("--do-it", dest="do_it", action="store_true")

    def handle(self, *args, **options):
        count = 0
        ibs_to_resync = set()
        last_written_ibs = set()
        if self.journal_file.exists():
            with self.journal_file.open() as f:
                last_written_ibs = set(map(int, f))
                logger.info("Restored %d ib ids from journal", len(last_written_ibs))
            ibs_to_resync |= last_written_ibs

        for titles in find_mergeable_titles():
            print("------------")
            for title in titles:
                print(
                    ", ".join(
                        map(
                            str,
                            [
                                title.pk,
                                title.name,
                                title.pub_type,
                                title.issn,
                                title.eissn,
                                title.isbn,
                                title.doi,
                                title.proprietary_ids,
                            ],
                        )
                    )
                )
            count += 1
            if options["do_it"]:
                with atomic():
                    winner, resync = merge_titles(titles, skip_ch_sync=True)
                ibs_to_resync |= resync
                new_ibs = ibs_to_resync - last_written_ibs
                if new_ibs:
                    with self.journal_file.open("a") as f:
                        f.writelines(f"{ib}\n" for ib in new_ibs)
                    last_written_ibs |= new_ibs
        logger.info("Total count: %d, IBs to resync: %d", count, len(ibs_to_resync))

        if options["do_it"] and ibs_to_resync:
            ch_backend.delete_records(
                AccessLogCube.query().filter(import_batch_id__in=list(ibs_to_resync))
            )
            sync_accesslogs_with_clickhouse_superfast(ignore_timestamps=True, ib_ids=ibs_to_resync)
            self.journal_file.unlink()
        else:
            logger.warning("Nothing has changed - for merge use --do-it")
