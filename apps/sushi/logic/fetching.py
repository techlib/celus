"""
Stuff related to fetching data from SUSHI servers.
"""
import logging
from collections import Counter
from datetime import timedelta
from time import sleep

from django.db.models import Count
from django.utils.timezone import now

from nigiri.client import SushiClientBase
from sushi.models import SushiFetchAttempt


logger = logging.getLogger(__name__)


def retry_queued(number=0, sleep_interval=0) -> Counter:
    """
    Goes over the queued SushiFetchAttempts and decides if it makes sense to redownload them.
    If yes, it does so.
    :return:
    """
    # no reason redownloading those where download was not successful - this has to be done
    # manually
    qs = SushiFetchAttempt.objects.filter(queued=True, processing_success=True).\
        annotate(following_count=Count('queue_following')).filter(following_count=0).\
        order_by('-when_queued')
    logger.debug('Found %s attempts to retry', qs.count())
    last_platform = None
    stats = Counter()
    for i, attempt in enumerate(qs):
        exp = SushiClientBase.explain_error_code(attempt.error_code)
        delta = exp.retry_interval_timedelta if exp else timedelta(days=30)
        if attempt.when_queued is None or (delta and attempt.when_queued + delta < now()):
            # we are ready to retry
            logger.debug('Retrying attempt: %s', attempt)
            new = attempt.retry()
            logger.debug('Result: %s', new)
            stats[f'retry_{new.status}'] += 1
            if attempt.credentials.platform_id == last_platform:
                sleep(sleep_interval)
            last_platform = attempt.credentials.platform_id
        else:
            # not yet time to retry
            if delta:
                remaining = attempt.when_queued + delta - now()
                logger.debug('Too soon to retry - need %s', remaining)
                stats['too soon'] += 1
            else:
                logger.debug('Should not retry automatically')
                stats['no auto'] += 1
        if number and i >= number - 1:
            break
    return stats
