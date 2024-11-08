import logging
from collections import Counter
from datetime import timedelta
from typing import List, Optional

import pandas as pd
from core.models import DATA_SOURCE_TYPE_API, DATA_SOURCE_TYPE_KNOWLEDGEBASE
from django.conf import settings
from django.db.models import DurationField, ExpressionWrapper, F, FloatField, Min, Value
from django.db.models.functions import Extract
from django.utils import timezone
from sushi.models import SushiFetchAttempt

from publications.models import DEFAULT_ARRIVAL_STATS, Platform

logger = logging.getLogger(__name__)


def create_table_from_db(platform_id: Optional[int], lookback_days: Optional[int] = 365):
    """
    :param platform_id: platform id
    :param lookback_days: number of days to look back when loading data - None means unlimited
    :return:
    """

    if platform_id is None:
        table = SushiFetchAttempt.objects.all().filter(
            credentials__platform__source__type__in=(
                DATA_SOURCE_TYPE_KNOWLEDGEBASE,
                DATA_SOURCE_TYPE_API,
            )
        )  # universal model - all fetch attempts, but only for "trustworthy" sources
    else:
        table = SushiFetchAttempt.objects.filter(credentials__platform_id=platform_id)
    look_back_filter = {}
    if lookback_days is not None:
        look_back_filter["when_processed__gte"] = timezone.now() - timedelta(days=lookback_days)
    table_values = (
        table.annotate(
            age=ExpressionWrapper(
                F("when_processed") - F("start_date"), output_field=DurationField()
            ),
            delay=ExpressionWrapper(
                Extract(
                    ExpressionWrapper(
                        F("when_processed") - F("end_date"), output_field=DurationField()
                    ),
                    "epoch",  # convert to seconds
                )
                / Value(60 * 60 * 24)  # convert seconds to days
                - Value(1),  # end_date is month end, we adjust to month start
                output_field=FloatField(),
            ),
        )
        .filter(
            age__lte=timedelta(
                days=75
            ),  # start_date is always month start, so we need to add ~30 days
            import_batch_id__isnull=False,
            credentials__counter_version=5,
            when_processed__isnull=False,
            delay__gte=0,  # remove negative delays, these are flukes
            **look_back_filter,
        )
        .values("start_date", "credentials_id", "counter_report_id")  # consider each RT separately
        .annotate(delay=Min("delay"))
        .order_by("delay")
    )
    df = pd.DataFrame.from_records(table_values)
    return df


def get_probabilities(
    platform_id: Optional[int], lookback_days: Optional[int] = 365
) -> (int, List[int]):
    data = create_table_from_db(platform_id, lookback_days=lookback_days)
    if not len(data):
        return 0, [0] * len(settings.SUSHI_ARRIVAL_STATS_QUANTILES)
    return (
        len(data),
        data["delay"]
        .quantile(settings.SUSHI_ARRIVAL_STATS_QUANTILES, interpolation="linear")
        .values.tolist(),
    )


def update_all_arrival_curves(attempt_count_threshold=10, lookback_days=365):
    """
    Unless the platform has at least attempt_count_threshold attempts, it will use the generic curve
    """
    stats = Counter()
    quantiles = settings.SUSHI_ARRIVAL_STATS_QUANTILES

    # test if there are enough attempts to create a generic curve
    # if not, we will use the default curve - see the description of the DEFAULT_ARRIVAL_STATS
    generic_count, generic_curve = get_probabilities(None, lookback_days=lookback_days)
    if generic_count < attempt_count_threshold:
        generic_curve = DEFAULT_ARRIVAL_STATS["curve"]
        quantiles = DEFAULT_ARRIVAL_STATS["probabs"]

    for platform in Platform.objects.all():
        count, curve = get_probabilities(platform.id, lookback_days=lookback_days)
        if count >= attempt_count_threshold:
            curve_source = "specific"
        else:
            curve_source = "generic"
            curve = generic_curve
        platform.sushi_arrival_stats = {
            "curve": curve,
            "source": curve_source,
            "count": count,
            "probabs": quantiles,
        }
        platform.save(update_fields=["sushi_arrival_stats"])
        stats[curve_source] += 1
    logger.debug("Arrival curves updated: %s", stats)
