import logging
from collections import Counter
from time import monotonic

from django.core.management.base import BaseCommand
from django.db.models import F, OuterRef, Q, Subquery
from organizations.models import Organization
from publications.models import Platform

from logs.logic.interest.computation import (
    find_superseded_import_batches,
    get_report_types_superseded_by_report_type,
    recompute_interest_by_batch,
)
from logs.models import ImportBatch, ReportType

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Look for cases where an import batch with no records superseded a non-empty one and "
        "recompute interest"
    )

    def add_arguments(self, parser):
        parser.add_argument("-p", dest="platform", help="short name of the platform to process")
        parser.add_argument(
            "-r", dest="report_type", help="short name of the report_type to process"
        )
        parser.add_argument(
            "-o", dest="organization", help="short name or ID of the organization to process"
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="debug mode - show info about individual import batches",
        )

    def handle(self, *args, **options):
        filters = {}
        report_types = ReportType.objects.filter(supersedes__isnull=False)

        if options["platform"]:
            filters["platform_id"] = Platform.objects.get(short_name=options["platform"]).pk
        if options["report_type"]:
            report_types = report_types.filter(short_name=options["report_type"])
            if not report_types.exists():
                logger.error(
                    "Report type %s is not superseding or does not exist", options["report_type"]
                )
                return
        if options["organization"]:
            # Try to get organization by ID first, then by short_name
            try:
                org_id = int(options["organization"])
                organization = Organization.objects.get(pk=org_id)
            except (ValueError, Organization.DoesNotExist):
                # If not an ID or not found, try by short_name
                organization = Organization.objects.get(short_name=options["organization"])
            filters["organization_id"] = organization.pk

        qs = ImportBatch.objects.filter(**filters)
        start = monotonic()
        stats = Counter()
        ib_count = 0
        interest_rt = ReportType.objects.get_interest_rt()
        unique_orgs = set()
        unique_platforms = set()
        for rt2 in report_types:
            superseder_rts = get_report_types_superseded_by_report_type(rt2)
            # the interest computation will deal with indirect superseding, by using the
            # most appropriate superseding report type. Here we just need to find all
            # the candidates for replacement, order is not important.
            batch_qs = qs.annotate(
                to_replace_ib=Subquery(
                    ImportBatch.objects.filter(
                        report_type__in=superseder_rts,
                        record_count__gt=0,
                        platform_id=OuterRef("platform_id"),
                        organization_id=OuterRef("organization_id"),
                        date=OuterRef("date"),
                    ).values("pk")[:1]
                )
            ).filter(
                (Q(interest_ib__isnull=True) | Q(interest_ib=F("pk"))),
                to_replace_ib__isnull=False,
                report_type=rt2,
                record_count=0,
            )
            batch_ib_count = batch_qs.count()
            if batch_ib_count == 0:
                logger.info("No batches to process for %s", rt2.short_name)
                continue
            logger.info("Going to process %d batches for %s", batch_ib_count, rt2.short_name)
            ib_count += batch_ib_count
            unique_orgs.update(batch_qs.values_list("organization_id", flat=True))
            unique_platforms.update(batch_qs.values_list("platform_id", flat=True))

            # start from the non-empty side
            # this is not very efficient, but it makes sure that we get all the relevant
            # import batches, even when TR supersedes both JR1 and BR2.
            replacement_ibs = set()
            for ib in batch_qs:
                ss_ibs = find_superseded_import_batches(ib, no_emptiness_check=True)
                if options["debug"]:
                    for replacement_ib in ss_ibs:
                        logger.info(
                            "Batch #%d: '%s', '%s', '%s', '%s' to be replaced by %s (#%d)",
                            ib.pk,
                            ib.report_type.short_name,
                            ib.organization.short_name,
                            ib.platform.short_name,
                            ib.date,
                            replacement_ib.report_type.short_name,
                            replacement_ib.pk,
                        )
                        if replacement_ib.report_type.superseded_by_id != rt2.pk:
                            # extra warning log for indirect superseding
                            logger.warning(
                                "Indirect superseding: #%d: '%s', '%s', '%s', '%s' to be replaced "
                                "by %s (#%d)",
                                ib.pk,
                                ib.report_type.short_name,
                                ib.organization.short_name,
                                ib.platform.short_name,
                                ib.date,
                                replacement_ib.report_type.short_name,
                                replacement_ib.pk,
                            )
                replacement_ibs.update({ib.id for ib in ss_ibs})

            batch_stats = recompute_interest_by_batch(
                ImportBatch.objects.filter(pk__in=replacement_ibs), interest_rt=interest_rt
            )

            # now also from the empty import batch side
            batch_stats |= recompute_interest_by_batch(batch_qs, interest_rt=interest_rt)

            logger.info("Batch for %s recomputed: %s", rt2.short_name, batch_stats)
            stats.update(batch_stats)

        logger.info("Duration: %s, Stats: %s", monotonic() - start, stats)
        logger.info(
            "ImportBatches: %d; speed: %.1f ib/s", ib_count, ib_count / (monotonic() - start)
        )
        logger.info("Unique platforms involved: %d", len(unique_platforms))
        for p in Platform.objects.filter(pk__in=unique_platforms):
            logger.info("%d, %s, %s", p.pk, p.short_name, p.name)

        logger.info("Unique organizations involved: %d", len(unique_orgs))

        for o in Organization.objects.filter(pk__in=unique_orgs):
            logger.info("%d, %s, %s", o.pk, o.short_name, o.name)
