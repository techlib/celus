import logging
from collections import Counter

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from logs.logic.materialized_interest import INTEREST_DEFAULT_REPORT_TYPES
from logs.models import InterestGroup, Metric, ReportInterestMetric, ReportType

logger = logging.getLogger(__name__)


def convert_short_name(code: str, counter_version: int) -> str:
    """short_name conversion for Counter 5.1"""
    if counter_version == 51:
        return code + "51"
    else:
        return code


class Command(BaseCommand):
    help = "Checks that the interest for standard reports is set up correctly"

    def add_arguments(self, parser):
        parser.add_argument("--fix-it", dest="fix_it", action="store_true")

    @atomic
    def handle(self, *args, **options):
        stats = Counter()
        code_to_rt = {rt.short_name: rt for rt in ReportType.objects.all()}
        short_name_to_metric = {m.short_name: m for m in Metric.objects.all()}
        short_name_to_ig = {ig.short_name: ig for ig in InterestGroup.objects.all()}
        for (cver, rep_code), definition in INTEREST_DEFAULT_REPORT_TYPES.items():
            changed = False
            rep_code = convert_short_name(rep_code, cver)

            # TODO these lines can be simplified once we remove ENABLE_ITEMS option
            # and Item Reports became mandatory
            if not (rt := code_to_rt.get(rep_code)):
                logger.warning("Can't find report type with short name '%s'", rep_code)
                continue

            sb_rt = None
            if sb := definition.get("superseded_by"):
                sb_rep_code = convert_short_name(sb[1], sb[0])
                sb_rt = code_to_rt.get(sb_rep_code)
            if rt.superseded_by != sb_rt:
                rt.superseded_by = sb_rt
                logger.info("Updated superseded_by for %s to %s", rt, sb_rt)
                stats["updated_superseded_by"] += 1
                changed = True
            if not rt.default_platform_interest:
                # all default reports should have default_platform_interest set to True
                rt.default_platform_interest = True
                logger.info("Set default_platform_interest to true for %s", rt)
                stats["updated_default_platform_interest"] += 1
                changed = True

            if changed:
                rt.save()
            else:
                logger.debug("No change for %s", rt)
                stats["unchanged"] += 1

            # check interest metrics
            seen_metric_ig_ids = set()
            for interest, idef in definition["interest"].items():
                ig = short_name_to_ig[interest]
                for metric_name in idef["metrics"]:
                    metric = short_name_to_metric[metric_name]
                    rim, created = ReportInterestMetric.objects.get_or_create(
                        report_type=rt, interest_group=ig, metric=metric
                    )
                    if created:
                        logger.info("Added RIM %s", rim)
                        stats["RIM added"] += 1
                    seen_metric_ig_ids.add((metric.pk, ig.pk))
            # remove all RIMs that are not in the definition
            for rim in ReportInterestMetric.objects.filter(report_type=rt):
                if (rim.metric.pk, rim.interest_group.pk) not in seen_metric_ig_ids:
                    rim.delete()
                    logger.info("Deleted RIM %s", rim)
                    stats["RIM deleted"] += 1

        logger.info("Stats: %s", stats)

        if not options["fix_it"]:
            raise ValueError("Dry run. To actually make the changes, use --fix-it")
