import logging
from collections import Counter

from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from logs.models import ReportType

from sushi.models import (
    CounterReportType,
    CounterVersionChoices,
    SushiCredentials,
    SushiFetchAttempt,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Searches through all SushiCredentials and updates the URL if it matches the original one. "
        "Optionally credentials may be filtered by platform. If the credentials are "
        "verified, a fake fetch attempt is created for the new URL, so that it remains verified."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--counter-version", type=CounterVersionChoices, default=CounterVersionChoices.C5
        )
        parser.add_argument("-p", dest="platform", help="short name of the platform to process")
        parser.add_argument("original", type=str, help="Original url")
        parser.add_argument("new", type=str, help="New url")
        parser.add_argument("--do-it", dest="do_it", action="store_true")

    @atomic
    def handle(self, *args, **options):
        qs = SushiCredentials.objects.filter(counter_version=options["counter_version"])
        stats = Counter()
        if options["platform"]:
            qs = qs.filter(platform__short_name=options["platform"])
        logger.info("Checking %d credentials", qs.count())
        fake_report = self.create_fake_report()
        for cr in qs:
            was_verified = cr.is_verified
            if cr.url.rstrip("/") == options["original"].rstrip("/"):
                cr.url = options["new"]
                cr.save()
                logger.info("Updated %s", cr)
                stats["updated"] += 1
                if was_verified:
                    self.create_fake_attempt(fake_report, cr)
            elif cr.url.rstrip("/") == options["new"].rstrip("/"):
                logger.info("Skipping %s (url is already up to date)", cr)
                stats["up to date"] += 1
            else:
                logger.info("Skipping %s (url is '%s', not '%s')", cr, cr.url, options["original"])
                stats["skipped"] += 1

        logger.info("Stats: %s", stats)
        if not options["do_it"]:
            logger.info("Dry run, use --do-it to actually update the credentials")
            raise ValueError("Dry run")

    def create_fake_report(self):
        rt, _ = ReportType.objects.get_or_create(short_name="_foo", name="_FOO")
        return CounterReportType.objects.get_or_create(
            code="_foo", report_type=rt, counter_version=7
        )[0]

    def create_fake_attempt(self, report, cr):
        return SushiFetchAttempt.objects.create(
            credentials=cr,
            status="no_data",
            start_date="2024-03-01",
            end_date="2024-03-31",
            counter_report=report,
            file_size=0,
        )
