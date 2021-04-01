from collections import Counter
import logging

from django.db.models import Exists, OuterRef

from logs.models import AccessLog
from publications.models import PlatformTitle


logger = logging.getLogger(__name__)


def clean_obsolete_platform_title_links(pretend=False):
    """
    Doing it in one query is possible, but takes a very long time. Therefore
    we go by platform-organization tuples.
    :return:
    """
    stats = Counter()
    for platform_id, organization_id in PlatformTitle.objects.values_list(
        'platform_id', 'organization_id'
    ).distinct():
        accesslog_query = AccessLog.objects.filter(
            organization=organization_id,
            platform=platform_id,
            target=OuterRef('title'),
            date=OuterRef('date'),
        )
        qs = (
            PlatformTitle.objects.filter(organization_id=organization_id, platform_id=platform_id)
            .annotate(valid=Exists(accesslog_query))
            .exclude(valid=True)
        )
        if pretend:
            count = qs.count()
            stats['removed'] += count
        else:
            count, details = qs.delete()
            stats['removed'] += count
        logger.debug('%5d %5d %6d', platform_id, organization_id, count)
    return stats
