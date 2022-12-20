import logging
from contextlib import contextmanager
from time import sleep, time

from django.core.cache import cache
from redis.exceptions import LockError

logger = logging.getLogger(__name__)


@contextmanager
def cache_based_lock(lock_name, timeout=3600, blocking_timeout=None):
    if hasattr(cache, 'lock'):
        with cache.lock(lock_name, timeout=timeout, blocking_timeout=blocking_timeout):
            yield None
    else:
        # cache does not support locking, we use a poor mans solution
        is_free = cache.add(lock_name, 1, timeout)
        start_time = time()
        if not is_free:
            logger.warning("Task is locked. Waiting for lock release of '{}'".format(lock_name))
        while not is_free:
            if blocking_timeout and time() - start_time > blocking_timeout:
                raise LockError('Blocking timeout')
            sleep(0.5)
            is_free = cache.add(lock_name, 1, timeout)
        logger.info("Task is free to run")
        lock_time = time()
        try:
            yield None
        finally:
            if time() < lock_time + timeout:
                # the lock has not yet timed out, so it should be ours
                cache.delete(lock_name)
