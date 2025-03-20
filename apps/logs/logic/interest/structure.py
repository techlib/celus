from typing import List

from logs.models import Metric


def get_interest_metrics() -> List[Metric]:
    """
    It returns the metrics which are used to encode the interest types.
    """
    return Metric.objects.filter(interest_group__isnull=False)


def get_interest_metrics_implying_availability() -> List[Metric]:
    """
    It returns the metrics which are used to encode the interest types which imply availability.
    """
    return Metric.objects.filter(interest_group__implies_availability=True)
