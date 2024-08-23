import logging
import threading
from collections import Counter
from functools import wraps

import celery
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from logs.cubes import ch_backend

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


def logged_task(fn):
    """
    Decorator for Celery tasks that logs the number of queries and stores it in the cache to be
    picked up later by the logger
    """

    @wraps(fn)
    def decorated(*args, **kwargs):
        counter = Counter()

        def wrapper(execute, sql, params, many, context):
            nonlocal counter
            counter[threading.get_ident()] += 1
            return execute(sql, params, many, context)

        tid = threading.get_ident()
        start_ch_qc = (
            ch_backend._query_counts.get(tid, {}).get("AccessLogCube", 0)
            if settings.CLICKHOUSE_QUERY_ACTIVE
            else 0
        )
        with connection.execute_wrapper(wrapper):
            # here we run the actual task
            out = fn(*args, **kwargs)

            # and log the number of queries that were executed
            task_id = celery.current_task.request.id
            cache.set(f"celery_task_query_count_{task_id}", counter[tid], 60 * 60)

        end_ch_qc = (
            ch_backend._query_counts.get(tid, {}).get("AccessLogCube", 0)
            if settings.CLICKHOUSE_QUERY_ACTIVE
            else 0
        )
        cache.set(f"celery_task_ch_query_count_{task_id}", end_ch_qc - start_ch_qc, 60 * 60)
        logger.debug(
            "Executed %d django queries and %d clickhouse queries in %s",
            counter[tid],
            end_ch_qc - start_ch_qc,
            fn.__name__,
        )
        return out

    return decorated
