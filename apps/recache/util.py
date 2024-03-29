import logging
from datetime import timedelta
from time import monotonic

import django
from django.db import IntegrityError
from django.db.transaction import atomic

from .models import DEFAULT_LIFETIME, DEFAULT_TIMEOUT, EMPTY_RESULT_DURATION_THRESHOLD, CachedQuery
from .tasks import find_and_renew_first_due_cached_query_task

logger = logging.getLogger(__name__)


@atomic
def recache_queryset(
    queryset,
    timeout: timedelta = DEFAULT_TIMEOUT,
    lifetime: timedelta = DEFAULT_LIFETIME,
    origin: str = '',
):
    """
    Given a queryset, it returns an evaluated queryset and does all the necessary caching stuff
    in the background.
    - queryset it cached
      - it has wrong django version -> remove it and create new cache
      - it is still valid -> return the cached data
      - it is not valid but not too old -> return the cached data + initialize renewal
      - it is too old -> renew and return the new data
    - queryset is not cached
      - create a new cache
    """
    logger.debug('Recaching queryset')
    try:
        cq: CachedQuery = CachedQuery.objects.select_for_update().get_for_queryset(queryset)
        logger.debug('Found existing version: %s (last update: %s)', cq, cq.last_updated)
        if cq.django_version != django.get_version():
            logger.debug(
                'Stored version is from old Django version, removing: %s vs %s)',
                cq.django_version,
                django.get_version(),
            )
            # delete should be thread safe because select_for_update() above locked the db row
            cq.delete()
            safe_create_cached_query(queryset, timeout, lifetime, origin)
            return queryset
        if cq.is_valid:
            logger.debug('Returning valid cached version')
            return cq.get_cached_queryset()
        if not cq.is_too_old:
            logger.debug('Cache slightly stale - returning cached version and scheduling renewal')
            qs = cq.get_cached_queryset()
            find_and_renew_first_due_cached_query_task.apply_async()
            return qs
        # it is too old, we need to re-evaluate before returning data
        logger.debug('Stale cache - renewing cache, scheduling next renew and returning new data')
        cq.renew()
        return cq.get_cached_queryset()
    except CachedQuery.DoesNotExist:
        start = monotonic()
        result_count = len(queryset)  # evaluate the queryset to get the duration
        duration = monotonic() - start
        if result_count == 0 and duration < EMPTY_RESULT_DURATION_THRESHOLD:
            logger.debug('Not caching empty result for a fast (%.2f s) query', duration)
            return queryset
        logger.debug('Creating new cache')
        safe_create_cached_query(queryset, timeout, lifetime, origin)
        return queryset


def safe_create_cached_query(queryset, timeout, lifetime, origin):
    try:
        # we need to do this atomic otherwise the exception would roll back an open transaction
        # outside this function
        with atomic():
            return CachedQuery.objects.create_from_queryset(
                queryset, timeout=timeout, lifetime=lifetime, origin=origin
            )
    except IntegrityError as exc:
        # the object might have been already created in a parallel thread,
        # we simply ignore it and return the queryset
        # the worst that can happen is that there would be no cache created
        logger.info(
            'Could not create CachedQuery, probably due to race condition in its creation: %s', exc
        )
    return None
