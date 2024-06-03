"""
This command reimports all IR_M1 counter reports from titles to items.
It is constructed so that it removes all the old data synchronously and then
plans the new data to be imported asynchronously.

This means that at the end, we can sync the platform title links already
because the obsolete connections will be removed.
"""

import logging
from collections import Counter

from django.core.management.base import BaseCommand
from publications.logic.cleanup import sync_platform_title_links
from sushi.models import AttemptStatus, SushiFetchAttempt

from logs.logic.attempt_import import import_one_sushi_attempt
from logs.models import ImportBatch, ManualDataUpload, MduMethod, MduState
from logs.tasks import reprocess_mdu_task

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Plans to reimport all IR_M1 counter reports"

    def add_arguments(self, parser):
        parser.add_argument("--do-it", dest="do_it", action="store_true")
        parser.add_argument(
            "--delete-obsolete-ibs", dest="delete_obsolete_ibs", action="store_true"
        )

    def handle(self, *args, **options):
        # the common trick of using atomic() to pretend the changes
        # would in this case create a large transaction which than puts much
        # stress on the database
        # Therefore we do not do any changes unless --do-it is used
        # and do not use atomic()
        self.reimport_attempts(options["do_it"], options["delete_obsolete_ibs"])

    def reimport_attempts(self, do_it: bool, delete_obsolete_ibs: bool):
        stats = Counter()
        # I found that in K1, we have some attempts with status IMPORT_FAILED
        # which contain data and have the clashing_import_batch_id set to the same value
        # as the import_batch_id.
        # This is strange, but we need to reprocess it anyway, so I only exclude NO_DATA
        # instead of including just SUCCESS.
        base_qs = SushiFetchAttempt.objects.filter(
            counter_report__report_type__short_name="IR_M1", import_batch__isnull=False
        ).exclude(status=AttemptStatus.NO_DATA)

        # Reimport fetch attempts with credentials - just plan their reimport in celery
        attempts = base_qs.filter(credentials__isnull=False)
        total = attempts.count()
        for i, attempt in enumerate(attempts):
            if attempt.status != AttemptStatus.SUCCESS:
                logger.warning(
                    "Attempt %d/%d: %s has strange status %s, but reimporting anyway",
                    i + 1,
                    total,
                    attempt,
                    attempt.status,
                )
                stats["attempts_with_strange_status"] += 1
            if do_it:
                attempt.reimport()
            stats["attempts"] += 1
            logger.debug("Planned to reprocess attempt %d/%d: %s", i + 1, total, attempt)

        # Reimport fetch attempts without credentials - these need to be treated differently
        # because they do not have credentials and we need to provide the necessary information
        # based on the import batch data
        attempts = base_qs.filter(credentials__isnull=True)
        total = attempts.count()
        for i, attempt in enumerate(attempts):
            stats["attempts_without_credentials"] += 1
            logger.warning(
                "Attempt without credentials - immediate reimport %d/%d: #%d, platform: %s, "
                "organization: %s",
                i + 1,
                total,
                attempt.pk,
                attempt.import_batch.platform.name,
                attempt.import_batch.organization.name,
            )
            if do_it:
                # get the organization and platform from the import batch before deleting it
                organization = attempt.import_batch.organization
                platform = attempt.import_batch.platform
                attempt.reimport()
                import_one_sushi_attempt(
                    attempt, organization=organization, platform=platform, counter_version=5
                )

        logger.info(
            "Reprocessed %d attempts without credentials", stats["attempts_without_credentials"]
        )

        # Reimport MDUs
        mdu_qs = ManualDataUpload.objects.filter(
            report_type__short_name="IR_M1", state=MduState.IMPORTED, method=MduMethod.COUNTER
        )
        total = mdu_qs.count()
        for i, mdu in enumerate(mdu_qs):
            if do_it:
                mdu.import_batches.all().delete()
                mdu.state = MduState.IMPORTING
                mdu.error_details = None
                mdu.error = None
                mdu.when_processed = None
                mdu.save()
                reprocess_mdu_task.delay(mdu.pk)
            stats["mdu"] += 1
            logger.debug("Planned to reprocess mdu %d/%d: %s", i + 1, total, mdu)

        logger.info(f"Planned to reprocess {stats['mdu']} MDUs")

        # find obsolete importbatches - have neither sushi fetch attempts nor MDUs
        obsolete_ibs = ImportBatch.objects.filter(
            sushifetchattempt__isnull=True, mdu_link__isnull=True, report_type__short_name="IR_M1"
        )
        if obsolete_count := obsolete_ibs.count():
            stats["obsolete_ibs"] += obsolete_count
            logger.warning(
                f"Found {obsolete_count} obsolete import batches - they have neither sushi fetch "
                "attempts nor MDUs and thus cannot be re-imported"
            )
            if do_it and delete_obsolete_ibs:
                logger.warning("  Deleting obsolete import batches")
                obsolete_ibs.delete()
            else:
                logger.warning("  Use --do-it --delete-obsolete-ibs to delete them")

        # all of the above made sure that the old data is deleted and the new data is planned
        # so it is now ok for us to sync the platform title links
        if do_it:
            logger.info("Syncing platform title links")
            sync_platform_title_links()

        logger.info(f"Done, stats: {stats}")

        if not do_it:
            logger.error("Not doing anything - use --do-it to really make the changes")
