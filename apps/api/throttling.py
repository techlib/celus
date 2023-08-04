from core.logic.util import text_hash
from rest_framework.throttling import SimpleRateThrottle


class APIKeyBasedThrottle(SimpleRateThrottle):

    scope = 'remote_api'

    def get_cache_key(self, request, view):
        """
        Return the cache key for the current request.
        We use the value of the `Authorization` header as the key. This way if we give out
        multiple API keys to different users for the same organization, they will not interfere.
        """
        return text_hash(request.headers.get('Authorization', ''))
