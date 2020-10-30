import logging
from time import monotonic

import celery
import django

from core.logic.error_reporting import email_if_fails
from recache.models import CachedQuery, RenewalError

logger = logging.getLogger(__name__)


@celery.shared_task
@email_if_fails
def renew_cached_query_task(pk: int):
    """
    Renews `CachedQuery` object identified by primary key `pk`
    :param pk: primary key
    """
    try:
        cq = CachedQuery.objects.get(pk=pk)
    except CachedQuery.DoesNotExist:
        logger.debug('renew_cached_query: CachedQuery object not found: #%s', pk)
        return
    else:
        try:
            cq.renew()
        except RenewalError as exc:
            logger.warning('Renewal error (%s), deleting cache: %s', exc, cq)
            cq.delete()


@celery.shared_task
@email_if_fails
def find_and_renew_first_due_cached_query_task():
    """
    Finds the first `CachedQuery` that needs renewing, renews it and calls itself to process more caches
    """
    cq = CachedQuery.objects.past_timeout().first()
    if not cq:
        logger.debug('No CachedQuery for renewal found')
        return
    start = monotonic()
    try:
        cq.renew()
    except RenewalError as exc:
        logger.warning('Renewal error (%s), deleting cache: %s', exc, cq)
        cq.delete()
    else:
        logger.debug('Renewed cached query "%s" in %.2f s', cq, monotonic() - start)
    # call self (until no candidate is found)
    logger.debug('Looking for more due cached queries')
    find_and_renew_first_due_cached_query_task.apply_async()


@celery.shared_task
@email_if_fails
def remove_old_cached_queries_task():
    """
    Removes all `CachedQuery` past their lifetime
    """
    logger.info('Removing old cached queries: %s', CachedQuery.objects.past_lifetime().delete())
    logger.info(
        'Removing cached queries for different django version: %s',
        CachedQuery.objects.exclude(django_version=django.get_version()).delete(),
    )
