import logging
from collections import Counter
from datetime import date
from typing import Callable, Optional

from core.logic.debug import log_memory
from django.conf import settings
from django.db.models import QuerySet
from django.db.transaction import atomic
from logs.cubes import AccessLogCube, ch_backend
from logs.models import AccessLog, ImportBatch, OrganizationPlatform
from organizations.models import Organization
from publications.models import Platform, PlatformTitle
from scheduler.models import FetchIntention
from sushi.models import SushiFetchAttempt

logger = logging.getLogger(__name__)


def clean_obsolete_platform_title_links(pretend=False, batch_size=500_000):
    """
    Doing it in one query is possible, but takes a very long time. Therefor
    we go by organization. We also split the data into batches by month, so
    that we don't have to keep all the data in memory.

    The `batch_size` was experimentally determined to give reasonable speed and still
    not to consume much memory (in testing it was around 290 MB for the whole process).
    :return:
    """
    stats = Counter()
    memories = []

    def sync_batch(pts_from_logs: set, from_month: Optional[date], to_month: Optional[date]):
        fltrs = {'date__gte': from_month} if from_month else {}
        fltrs.update({'date__lt': to_month} if to_month else {})
        extra_pts = {
            pt_rec[0]
            for pt_rec in PlatformTitle.objects.filter(organization_id=org.pk, **fltrs)
            .values_list('pk', 'platform_id', 'title_id', 'date')
            .iterator()
            if (pt_rec[1], pt_rec[2], pt_rec[3]) not in pts_from_logs
        }
        count = len(extra_pts)
        stats['removed'] += count
        if not pretend and count > 0:
            PlatformTitle.objects.filter(pk__in=extra_pts).delete()
        logger.info('%s - %s, %d from %d', from_month, to_month, count, len(pts_from_logs))
        memories.append(log_memory('clean_obsolete_platform_title_links'))

    for org in Organization.objects.all():
        pts_in_logs = set()
        first_month = None
        last_month = None
        rec_date = None

        if settings.CLICKHOUSE_QUERY_ACTIVE:
            rec_gen = (
                (r.platform_id, r.target_id, r.date)
                for r in ch_backend.get_records(
                    AccessLogCube.query()
                    .filter(organization_id=org.pk)
                    .group_by('platform_id', 'target_id', 'date')
                    .order_by('date'),
                    streaming=True,
                )
            )
        else:
            rec_gen = (
                AccessLog.objects.filter(organization_id=org.pk)
                .values_list('platform_id', 'target_id', 'date')
                .order_by('date')
                .iterator()
            )

        for (rec_platform_id, rec_target_id, rec_date) in rec_gen:
            if last_month != rec_date:
                if len(pts_in_logs) > batch_size:
                    sync_batch(pts_in_logs, first_month, rec_date)
                    pts_in_logs = set()
                    first_month = rec_date

                last_month = rec_date
            pts_in_logs.add((rec_platform_id, rec_target_id, rec_date))
        sync_batch(pts_in_logs, first_month, rec_date)

    if memories:
        logger.info('max memory used: %.2f', max(memories))
    return stats


@atomic
def delete_platform_data(
    platform: Platform,
    organization_qs: QuerySet[Organization],
    delete_platform: bool = False,
    delete_credentials: bool = False,
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
            except Exception:
                # no error in progress monitor should influence this function
                pass

    stats = Counter()
    # import batches - deletes access logs as well
    _, substats = ImportBatch.objects.filter(
        platform=platform, organization__in=organization_qs
    ).delete()
    stats.update(substats)
    log_progress(30)

    _, substats = PlatformTitle.objects.filter(
        platform=platform, organization__in=organization_qs
    ).delete()
    stats.update(substats)
    log_progress(40)

    _, substats = OrganizationPlatform.objects.filter(
        platform=platform, organization__in=organization_qs
    ).delete()
    stats.update(substats)
    log_progress(50)

    fas = SushiFetchAttempt.objects.filter(
        credentials__platform=platform, credentials__organization__in=organization_qs
    )
    # we only delete intentions which have an attempt in order not to remove those that are
    # planned for later, etc.
    _, substats = FetchIntention.objects.filter(attempt__in=fas).delete()
    stats.update(substats)
    log_progress(60)

    # we also delete canceled FIs
    _, substats = FetchIntention.objects.filter(
        credentials__platform=platform, credentials__organization__in=organization_qs, canceled=True
    ).delete()
    stats.update(substats)
    log_progress(70)

    # delete the attempts
    _, substats = fas.delete()
    stats.update(substats)
    log_progress(80)

    # delete credentials
    if delete_credentials:
        _, substats = platform.sushicredentials_set.filter(
            organization__in=organization_qs
        ).delete()
        stats.update(substats)
        log_progress(85)

    if delete_platform and platform.source and platform.source.organization in organization_qs:
        _, substats = platform.delete()
        stats.update(substats)

    log_progress(90)
    return stats
