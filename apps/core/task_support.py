import logging
from contextlib import contextmanager

from django.core.cache import cache

logger = logging.getLogger(__name__)


@contextmanager
def cache_based_lock(lock_name, timeout=3600, blocking_timeout=None):
    with cache.lock(lock_name, timeout=timeout, blocking_timeout=blocking_timeout):
        yield None
