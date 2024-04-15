import logging
from datetime import timedelta
from time import time

from core.logic.util import this_celus_domain
from django.core.files.base import File
from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from tags.models import AccessibleBy, Tag, TagClass, TaggingBatch, TaggingBatchState, TagScope

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Processes a CSV title list and tags all the matched titles with tag specified on "
        "command line. If a tagging batch of the same name and with the same tags exists, it is "
        "updated and re-tagged."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "list_name", help="Internal name for the title list to allow re-tagging, deleting, etc."
        )
        parser.add_argument("tag_class")
        parser.add_argument("--class-desc", help="Description for the tag class", default="")
        parser.add_argument("tag_name")
        parser.add_argument("--tag-desc", help="Description for the tag", default="")
        parser.add_argument("title_list_file")
        parser.add_argument(
            "-d",
            "--delete",
            action="store_true",
            help="Delete previous tagging batch only - do not tag again.",
            dest="just_delete",
        )
        parser.add_argument(
            "--auto-retag",
            type=int,
            default=0,
            help="Turn on automatic re-tagging. Expects number in days",
        )
        parser.add_argument("--bg-color", help="Background color of the tag", default="#f0f0f0")
        parser.add_argument("--text-color", help="Text color of the tag", default="#000000")

    @atomic
    def handle(self, *args, **options):
        try:
            tb = TaggingBatch.objects.get(internal_name=options["list_name"])
        except TaggingBatch.DoesNotExist:
            tb = None

        if options["just_delete"]:
            if tb:
                logger.info("Deleting previous related tagging batch: %d", tb.pk)
                tb.delete()
            else:
                logger.warning("No previous related tagging batch found.")
            return

        reprocess_after = timedelta(days=options["auto_retag"]) if options["auto_retag"] else None
        with open(options["title_list_file"], "rb") as infile:
            file_content = File(infile)

            if not tb:
                tag_class, created = TagClass.objects.get_or_create(
                    name=options["tag_class"],
                    internal=True,
                    scope=TagScope.TITLE,
                    defaults=dict(
                        exclusive=False,
                        desc=options["class_desc"],
                        can_modify=AccessibleBy.SYSTEM,
                        can_create_tags=AccessibleBy.SYSTEM,
                        default_tag_can_see=AccessibleBy.EVERYBODY,
                        default_tag_can_assign=AccessibleBy.SYSTEM,
                        bg_color=options["bg_color"],
                        text_color=options["text_color"],
                    ),
                )
                if created:
                    logger.info("Created new internal tag class: %s", tag_class.name)
                else:
                    logger.info("Using existing internal tag class: %s", tag_class.name)

                if options["tag_name"].strip():
                    tag_class_to_use = None
                    tag, created = Tag.objects.get_or_create(
                        name=options["tag_name"],
                        tag_class=tag_class,
                        defaults=dict(
                            desc=options["tag_desc"],
                            can_see=AccessibleBy.EVERYBODY,
                            can_assign=AccessibleBy.SYSTEM,
                            bg_color=options["bg_color"],
                            text_color=options["text_color"],
                        ),
                    )
                    if created:
                        logger.info("Created new internal tag: %s", tag.name)
                    else:
                        logger.info("Using existing internal tag: %s", tag.name)
                else:
                    logger.info("No tag name given, expecting tags from input file.")
                    tag = None
                    tag_class_to_use = tag_class

                tb = TaggingBatch.objects.create(
                    internal_name=options["list_name"],
                    tag=tag,
                    tag_class=tag_class_to_use,
                    source_file=file_content,
                    state=TaggingBatchState.IMPORTING,
                    reprocess_after=reprocess_after,
                )
            else:
                tb.state = TaggingBatchState.IMPORTING
                tb.source_file = file_content
                if not tb.reprocess_after and reprocess_after:
                    # update reprocess_after if given
                    tb.reprocess_after = reprocess_after
                tb.save()

        last_log = time()

        def progress_monitor(current, total):
            nonlocal last_log
            if time() - last_log < 1:
                return
            logger.info("Progress: %d / %d (%.1f %%)", current, total, current / total * 100)
            last_log = time()

        # re-fetch the tagging batch with a lock
        tb = TaggingBatch.objects.select_for_update(nowait=True).get(pk=tb.pk)

        domain_name = this_celus_domain()
        tb.assign_tag(
            title_id_formatter=lambda title_id: f"{domain_name}titles/{title_id}",
            progress_monitor=progress_monitor,
            system_process=True,
        )
