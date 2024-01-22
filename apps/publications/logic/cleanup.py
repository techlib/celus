import logging
from collections import Counter
from typing import Callable, Optional

from core.logic.debug import log_memory
from django.conf import settings
from django.db.models import QuerySet
from django.db.transaction import atomic
from logs.cubes import AccessLogCube, ch_backend
from logs.models import AccessLog, ImportBatch, OrganizationPlatform
from organizations.models import Organization
from scheduler.models import FetchIntention
from sushi.models import SushiFetchAttempt

from publications.models import Platform, PlatformTitle

logger = logging.getLogger(__name__)


def sync_platform_title_links(pretend=False):
    """
    Compares the AccessLog records with the PlatformTitle records and synchronizes
    the PlatformTitle records with the AccessLog records - by adding missing
    PlatformTitle records and removing extra PlatformTitle records.

    Doing it in one query is possible, but takes a very long time. Therefor
    we use batching by organization.
    """
    stats = Counter()
    memories = []

    for org in Organization.objects.all():
        # prepare a generator based on the AccessLog records
        if settings.CLICKHOUSE_QUERY_ACTIVE:
            rec_gen = (
                (r.platform_id, r.target_id, r.date)
                for r in ch_backend.get_records(
                    AccessLogCube.query()
                    .filter(organization_id=org.pk, target_id__not_in=[0])
                    .group_by("platform_id", "target_id", "date")
                    .order_by("platform_id", "target_id", "date"),
                    streaming=True,
                )
            )
        else:
            rec_gen = (
                AccessLog.objects.filter(organization_id=org.pk)
                .values_list("platform_id", "target_id", "date")
                .order_by("platform_id", "target_id", "date")
                .iterator()
            )
        # prepare a second generator based on the PlatformTitle records
        pt_gen = (
            PlatformTitle.objects.filter(organization_id=org.pk)
            .values_list("platform_id", "title_id", "date", "pk")
            .order_by("platform_id", "title_id", "date")
            .iterator()
        )
        # stats
        count = 0  # count records in pt_gen
        missing_pts = []
        extra_pts = []
        # iterate over both generators in parallel to find missing and extra records
        while True:
            if (pt_rec := next(pt_gen, None)) is None:
                break
            count += 1

            if (al_rec := next(rec_gen, None)) is None:
                extra_pts.append(pt_rec[3])
                break

            while pt_rec and pt_rec[:3] < al_rec:
                # everything extra in pt_rec goes to extra_pts
                extra_pts.append(pt_rec[3])
                if pt_rec := next(pt_gen, None):
                    count += 1

            while al_rec and pt_rec[:3] > al_rec:
                # everything extra in al_rec goes to missing_pts
                missing_pts.append(al_rec)
                al_rec = next(rec_gen, None)
        # gather extra stuff after one of the generators ended
        while al_extra := next(rec_gen, None):
            missing_pts.append(al_extra)
        while pt_extra := next(pt_gen, None):
            extra_pts.append(pt_extra[3])
            count += 1
        logger.info(
            "%s, total %d, extra %d, missing %d", org, count, len(extra_pts), len(missing_pts)
        )
        # missing platform-titles
        if missing_pts:
            stats["missing"] += len(missing_pts)
            if not pretend:
                PlatformTitle.objects.bulk_create(
                    PlatformTitle(
                        organization_id=org.pk, platform_id=key[0], title_id=key[1], date=key[2]
                    )
                    for key in missing_pts
                )
        # extra platform-titles
        if extra_pts:
            stats["removed"] += len(extra_pts)
            if not pretend:
                PlatformTitle.objects.filter(pk__in=extra_pts).delete()
        memories.append(log_memory("sync_platform_title_links"))

    if memories:
        logger.info("max memory used: %.2f", max(memories))
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
