import logging
from collections import Counter

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from logs.models import (
    Dimension,
    DimensionFilter,
    InterestConfig,
    ReportInterestMetric,
    ReportInterestMetricFilter,
    ReportType,
    ReportTypeToDimension,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Ensures DimensionFilters exist for Access_Type and Access_Method with specific values, "
        "removes these dimensions from the interest report type, and creates "
        "ReportInterestMetricFilter links for TR, IR, and DR report types "
        "(PR reports are not used for interest)"
    )

    def add_arguments(self, parser):
        parser.add_argument("--fix-it", dest="fix_it", action="store_true")

    @atomic
    def handle(self, *args, **options):
        stats = Counter()

        # ensure that only one interestprofile with organization=None exists
        interest_configs = InterestConfig.objects.filter(organization=None)
        if (icc := interest_configs.count()) > 1:
            logger.warning("Multiple (%d) interest profiles with organization=None found", icc)
            unique = interest_configs.filter(interest_profile__short_name="unique")
            if unique.count():
                logger.info(
                    "Deleted %d non-unique interest configs",
                    interest_configs.exclude(id__in=unique.values_list("id", flat=True))
                    .delete()[1]
                    .get("logs.InterestConfig", 0),
                )
            else:
                logger.error("No unique interest config found. Unresolvable state.")
                raise ValueError("No unique interest config found. Unresolvable state.")
        elif interest_configs.count() == 0:
            logger.info("No interest configs with organization=None found")
        else:
            logger.info("Only one interest config with organization=None found")

        # get the generic interest config and drop all filters from it
        generic_interest_config = InterestConfig.objects.get(organization__isnull=True)
        logger.info(
            "Deleted %d filters from the generic interest config",
            generic_interest_config.interest_filters.all()
            .delete()[1]
            .get("logs.DimensionFilter", 0),
        )

        # Define the required dimension filters
        required_filters = {"Access_Type": ["Controlled", None], "Access_Method": ["Regular", None]}

        # Get or create the required dimensions
        dimensions = {}
        for dim_short_name in required_filters.keys():
            try:
                dimensions[dim_short_name] = Dimension.objects.get(short_name=dim_short_name)
                logger.info("Found dimension: %s", dim_short_name)
            except Dimension.DoesNotExist:
                logger.warning("Dimension '%s' not found", dim_short_name)
                continue

        # Create DimensionFilters for each dimension
        created_filters = {}
        for dim_short_name, dimension in dimensions.items():
            values = required_filters[dim_short_name]
            dim_filter, created = DimensionFilter.objects.get_or_create(
                dimension=dimension, values=values, negated=False
            )
            if created:
                logger.info(
                    "Created DimensionFilter for %s with values: %s", dim_short_name, values
                )
                stats["dimension_filters_created"] += 1
            else:
                logger.info("DimensionFilter for %s already exists", dim_short_name)
                stats["dimension_filters_existing"] += 1

            created_filters[dim_short_name] = dim_filter

        # Find report types with short names TR, IR, DR and their 51 versions
        # Note: PR reports are not used for interest computation
        target_report_types = []
        for short_name in ["TR", "IR", "DR"]:
            # Find base version
            try:
                rt = ReportType.objects.get(short_name=short_name)
                target_report_types.append(rt)
                logger.info("Found report type: %s", rt.short_name)
            except ReportType.DoesNotExist:
                logger.warning("Report type '%s' not found", short_name)

            # Find 51 version
            try:
                rt_51 = ReportType.objects.get(short_name=f"{short_name}51")
                target_report_types.append(rt_51)
                logger.info("Found report type: %s", rt_51.short_name)
            except ReportType.DoesNotExist:
                logger.warning("Report type '%s51' not found", short_name)

        # Create ReportInterestMetricFilter links for each report type and dimension filter
        for report_type in target_report_types:
            # Determine which filters to apply based on report type
            # DR reports only use Access_Method, not Access_Type
            if report_type.short_name in ["DR", "DR51"]:
                applicable_filters = {
                    k: v for k, v in created_filters.items() if k == "Access_Method"
                }
                logger.info(
                    "DR report type %s: using only Access_Method filter", report_type.short_name
                )
            else:
                applicable_filters = created_filters
                logger.info("Report type %s: using all filters", report_type.short_name)

            for dim_filter in applicable_filters.values():
                # Get all ReportInterestMetrics for this report type
                rims = ReportInterestMetric.objects.filter(report_type=report_type)

                if not rims.exists():
                    logger.info(
                        "No ReportInterestMetrics found for report type: %s", report_type.short_name
                    )
                    continue

                for rim in rims:
                    # Check if the filter is already linked
                    existing_filter = ReportInterestMetricFilter.objects.filter(
                        report_interest_metric=rim, filter=dim_filter
                    ).first()

                    if not existing_filter:
                        # Create the link
                        ReportInterestMetricFilter.objects.create(
                            report_interest_metric=rim, filter=dim_filter
                        )
                        logger.info("Created ReportInterestMetricFilter: %s - %s", rim, dim_filter)
                        stats["rim_filters_created"] += 1
                    else:
                        logger.debug(
                            "ReportInterestMetricFilter already exists: %s - %s", rim, dim_filter
                        )
                        stats["rim_filters_existing"] += 1

        logger.info("Stats: %s", stats)

        # Remove Access_Type and Access_Method dimensions from the interest report type if present
        interest_rt = ReportType.objects.get_interest_rt()
        if interest_rt:
            for dim_short_name in ["Access_Type", "Access_Method"]:
                try:
                    dimension = Dimension.objects.get(short_name=dim_short_name)
                    # Check if this dimension is linked to the interest report type
                    rtd = ReportTypeToDimension.objects.filter(
                        report_type=interest_rt, dimension=dimension
                    ).first()
                    if rtd:
                        logger.info(
                            "Removing dimension %s from interest report type", dim_short_name
                        )
                        rtd.delete()
                        stats["dimensions_removed_from_interest"] += 1
                    else:
                        logger.debug(
                            "Dimension %s not present in interest report type", dim_short_name
                        )
                except Dimension.DoesNotExist:
                    logger.warning(
                        "Dimension '%s' not found for removal from interest report type",
                        dim_short_name,
                    )
        else:
            logger.warning("Interest report type not found")

        # Summary
        total_rims = ReportInterestMetric.objects.filter(
            report_type__in=target_report_types
        ).count()
        logger.info("Summary:")
        logger.info("- Processed %d report types", len(target_report_types))
        logger.info("- Created/verified %d dimension filters", len(created_filters))
        logger.info("- Total ReportInterestMetrics processed: %d", total_rims)

        if not options["fix_it"]:
            raise ValueError("Dry run. To actually make the changes, use --fix-it")
