import logging
from functools import wraps

from django.conf import settings

logger = logging.getLogger(__name__)


def needs_clickhouse_sync(fn):
    @wraps(fn)
    def ret(*args, **kwargs):
        if settings.CLICKHOUSE_SYNC_ACTIVE:
            return fn(*args, **kwargs)
        logger.warning(
            'Function "%s" requires clickhouse but clickhouse is not active', fn.__name__
        )
        return None

    return ret


def needs_clickhouse_query(fn):
    @wraps(fn)
    def ret(*args, **kwargs):
        if settings.CLICKHOUSE_QUERY_ACTIVE:
            return fn(*args, **kwargs)
        logger.warning(
            'Function "%s" requires clickhouse but clickhouse is not active', fn.__name__
        )
        return None

    return ret
