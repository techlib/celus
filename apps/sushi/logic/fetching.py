"""
Stuff related to fetching data from SUSHI servers.
"""
import logging
from datetime import datetime

from django.db.models import Count

from nigiri.client import SushiClientBase
from sushi.models import SushiFetchAttempt


logger = logging.getLogger(__name__)


def retry_queued(number=0):
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
    for i, attempt in enumerate(qs):
        exp = SushiClientBase.explain_error_code(attempt.error_code)
        delta = exp.retry_interval_timedelta
        if attempt.when_queued is None or (attempt.when_queued + delta > datetime.now()):
            # we are ready to retry
            logger.debug('Retrying attempt: %s', attempt)
            new = attempt.retry()
            logger.debug('Result: %s', new)
        else:
            # not yet time to retry
            remaining = datetime.now() - attempt.when_queued - delta
            logger.debug('Too soon to retry - need %s', remaining)
        if number and i >= number - 1:
            break
