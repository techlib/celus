import logging
from collections import Counter
from typing import Callable, Optional

from django.db.models import Exists, OuterRef, QuerySet
from django.db.transaction import atomic
from logs.models import AccessLog, ImportBatch, OrganizationPlatform
from organizations.models import Organization
from publications.models import Platform, PlatformTitle
from scheduler.models import FetchIntention
from sushi.models import SushiFetchAttempt

logger = logging.getLogger(__name__)


def clean_obsolete_platform_title_links(pretend=False):
    """
    Doing it in one query is possible, but takes a very long time. Therefor
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


@atomic
def delete_platform_data(
    platform: Platform,
    organization_qs: QuerySet[Organization],
    progress_monitor: Optional[Callable[[int, int], None]] = None,
) -> Counter:
    """
    Deletes all platform data for organizations specified by the `organization_qs`.
    If `progress_monitor` is given, it will be called to monitor progress. It will use percentage
    as progress measure, so the total (second argument) will be always 100.

    Returns a dict with all the deleted data.
    """

    def log_progress(num):
        if progress_monitor:
            try:
                progress_monitor(num, 100)
            except:
                # no error in progress monitor should influence this function
                pass

    stats = Counter()
    # import batches - deletes access logs as well
    _, substats = ImportBatch.objects.filter(
        platform=platform, organization__in=organization_qs
    ).delete()
    stats.update(substats)
    log_progress(50)

    _, substats = PlatformTitle.objects.filter(
        platform=platform, organization__in=organization_qs
    ).delete()
    stats.update(substats)
    log_progress(60)

    _, substats = OrganizationPlatform.objects.filter(
        platform=platform, organization__in=organization_qs
    ).delete()
    stats.update(substats)
    log_progress(70)

    fas = SushiFetchAttempt.objects.filter(
        credentials__platform=platform, credentials__organization__in=organization_qs
    )
    # we only delete intentions which have an attempt in order not to remove those that are
    # planned for later, etc.
    _, substats = FetchIntention.objects.filter(attempt__in=fas).delete()
    stats.update(substats)
    log_progress(80)

    # we also delete canceled FIs
    _, substats = FetchIntention.objects.filter(
        credentials__platform=platform, credentials__organization__in=organization_qs, canceled=True
    ).delete()
    stats.update(substats)
    log_progress(90)

    # delete the attempts
    _, substats = fas.delete()
    stats.update(substats)
    log_progress(99)

    return stats
