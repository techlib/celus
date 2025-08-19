import logging
from collections import Counter

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from logs.logic.get_or_create_with_map import get_or_create_with_map
from logs.logic.interest.definitions import (
    INTEREST_DEFAULT_REPORT_TYPES,
    create_default_interest_dimension_value_mappings,
    create_default_interest_groups,
    create_default_profiles,
    create_interest_rt,
)
from logs.models import (
    Dimension,
    DimensionFilter,
    InterestDimensionValueMapping,
    InterestGroup,
    Metric,
    ReportInterestMetric,
    ReportInterestMetricFilter,
    ReportType,
)

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
        interest_rt = create_interest_rt()
        interest_profiles = {p.short_name: p for p in create_default_profiles()}
        create_default_interest_dimension_value_mappings(interest_rt)
        create_default_interest_groups()

        code_to_rt = {rt.short_name: rt for rt in ReportType.objects.all()}
        short_name_to_metric_id = {m.short_name: {"pk": m.pk} for m in Metric.objects.all()}
        short_name_to_ig = {ig.short_name: ig for ig in InterestGroup.objects.all()}
        seen_rt_ids = set()
        for (cver, rep_code), definition in INTEREST_DEFAULT_REPORT_TYPES.items():
            changed = False
            rep_code = convert_short_name(rep_code, cver)

            # TODO these lines can be simplified once we remove ENABLE_ITEMS option
            # and Item Reports became mandatory
            if not (rt := code_to_rt.get(rep_code)):
                logger.warning("Can't find report type with short name '%s'", rep_code)
                continue

            seen_rt_ids.add(rt.pk)
            sb_rt = None
            if sb := definition.get("superseded_by"):
                sb_rep_code = convert_short_name(sb[1], sb[0])
                sb_rt = code_to_rt.get(sb_rep_code)
            if rt.superseded_by != sb_rt:
                rt.superseded_by = sb_rt
                logger.info("Updated superseded_by for %s to %s", rt, sb_rt)
                stats["updated_superseded_by"] += 1
                changed = True

            if changed:
                rt.save()
            else:
                logger.debug("No change for %s", rt)
                stats["unchanged"] += 1

            # check interest metrics
            seen_metric_ig_ids = set()
            for interest, idef in definition.get("interest", {}).items():
                ig = short_name_to_ig[interest]
                for metric_name, profile_name in idef["metrics"].items():
                    metric_id = get_or_create_with_map(
                        Metric, short_name_to_metric_id, "short_name", metric_name
                    )
                    profile = interest_profiles[profile_name] if profile_name else None
                    rim, created = ReportInterestMetric.objects.update_or_create(
                        report_type=rt,
                        interest_group=ig,
                        metric_id=metric_id,
                        defaults={"interest_profile": profile},
                    )
                    if created:
                        logger.info("Added RIM %s", rim)
                        stats["RIM added"] += 1
                    seen_metric_ig_ids.add((metric_id, ig.pk))
                    # check filters
                    for fltr in idef.get("filters", []):
                        dim = Dimension.objects.get(short_name=fltr["dimension"])
                        dimf = DimensionFilter.objects.get_or_create(
                            dimension=dim,
                            values=fltr.get("values", []),
                            negated=fltr.get("negate", False),
                        )[0]
                        ReportInterestMetricFilter.objects.get_or_create(
                            report_interest_metric=rim, filter=dimf
                        )
            # remove all RIMs that are not in the definition
            for rim in ReportInterestMetric.objects.filter(report_type=rt):
                if (rim.metric.pk, rim.interest_group.pk) not in seen_metric_ig_ids:
                    rim.delete()
                    logger.info("Deleted RIM %s", rim)
                    stats["RIM deleted"] += 1

            # check interest dimension value mappings
            for dimension_name, mdef in definition.get("mappings", {}).items():
                idim = Dimension.objects.get(short_name=dimension_name)
                srcdim = Dimension.objects.get(short_name=mdef["dimension"])

                src_rtdim = rt.reporttypetodimension_set.get(dimension=srcdim)
                InterestDimensionValueMapping.objects.update_or_create(
                    interest_rtdim=interest_rt.reporttypetodimension_set.get(dimension=idim),
                    source_rtdim=src_rtdim,
                    defaults={
                        "default_value": mdef.get("default"),
                        "mapping": mdef.get("values", {}),
                    },
                )

        # list all ReportInterestMetric objects which are connected to COUNTER reports and
        # were not hit above
        extra_rims = ReportInterestMetric.objects.filter(
            report_type__counterreporttype__isnull=False
        ).exclude(report_type__pk__in=seen_rt_ids)
        if extra_rims.exists():
            logger.warning("Removing obsolete COUNTER ReportInterestMetric not in definitions:")
            for rim in extra_rims:
                logger.warning(
                    "# %d: '%s' - '%s'", rim.pk, rim.metric.short_name, rim.report_type.short_name
                )
            count, _ = extra_rims.delete()
            logger.info("Deleted %d obsolete ReportInterestMetric objects", count)
            stats["obsolete RIM deleted"] += count

        # list all ReportTypes which have superseded_by set but have no interest metrics
        # these should be removed because they serve no purpose and may be confusing
        for rt in ReportType.objects.filter(superseded_by__isnull=False).exclude(
            reportinterestmetric__isnull=False
        ):
            stats["obsolete superseding removed"] += 1
            logger.warning(
                "ReportType %d '%s' has superseded_by set but has no interest metrics, removing it",
                rt.pk,
                rt.short_name,
            )
            rt.superseded_by = None
            rt.save()

        logger.info("Stats: %s", stats)

        if not options["fix_it"]:
            raise ValueError("Dry run. To actually make the changes, use --fix-it")
