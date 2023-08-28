import logging
import threading
from collections import Counter
from time import monotonic

from django.conf import settings
from django.contrib import auth
from django.contrib.auth import load_backend
from django.contrib.auth.middleware import RemoteUserMiddleware
from django.db import connection
from django.http import JsonResponse
from django.utils.translation import activate
from logs.cubes import ch_backend
from rest_framework import status

from core.auth import EDUIdAuthenticationBackend

logger = logging.getLogger(__name__)


class EDUIdHeaderMiddleware(RemoteUserMiddleware):

    header = settings.EDUID_IDENTITY_HEADER

    def process_request(self, request):
        logger.debug('Identity: %s', request.META.get(self.header))
        headers = [
            'HTTP_X_USER_ID',
            'HTTP_X_FULL_NAME',
            'HTTP_X_FIRST_NAME',
            'HTTP_X_LAST_NAME',
            'HTTP_X_USER_NAME',
            'HTTP_X_MAIL',
            'HTTP_X_CN',
            'HTTP_X_ROLES',
            'HTTP_X_IDENTITY',
        ]
        out = '; '.join(f'{header}: {request.META.get(header)}' for header in headers)
        logger.debug('Headers: %s', out)
        super().process_request(request)

    def _remove_invalid_user(self, request):
        """
        Remove the current authenticated user in the request which is invalid
        but only if the user is authenticated via the EDUIdAuthenticationBackend.

        This is a copy-paste based modification of the parent method
        """
        try:
            stored_backend = load_backend(request.session.get(auth.BACKEND_SESSION_KEY, ''))
        except ImportError:
            # backend failed to load
            auth.logout(request)
        else:
            if isinstance(stored_backend, EDUIdAuthenticationBackend):
                auth.logout(request)


class CelusVersionHeaderMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            'CELUS-VERSION' in request.headers
            and request.headers.get('CELUS-VERSION') != settings.CELUS_VERSION
        ):
            response = JsonResponse(
                {'error': 'celus versions mismatched'}, status=status.HTTP_409_CONFLICT
            )
        else:
            response = self.get_response(request)

        response['CELUS-VERSION'] = settings.CELUS_VERSION
        return response


class ClickhouseIntegrationMiddleware:
    """
    Adds `USE_CLICKHOUSE` attr to request based on global settings and per-request headers.

    Useful for testing, debugging etc.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.USE_CLICKHOUSE = settings.CLICKHOUSE_QUERY_ACTIVE and request.headers.get(
            'DISABLE-CLICKHOUSE'
        ) not in ('1', 'true')
        tid = threading.get_ident()
        start_query_count = ch_backend._query_counts.get(tid, {}).get('AccessLogCube', 0)
        response = self.get_response(request)
        end_query_count = ch_backend._query_counts.get(tid, {}).get('AccessLogCube', 0)
        response['X-Clickhouse-Query-Count'] = end_query_count - start_query_count
        return response


class UserLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user and hasattr(request.user, 'language'):
            activate(request.user.language)
        return self.get_response(request)


class QueryCounter:
    def __init__(self, log_all=None):
        self.counter = Counter()
        self.log_all = (
            log_all if log_all is not None else getattr(settings, 'LOG_ALL_QUERIES', False)
        )

    def __call__(self, execute, sql, params, many, context):
        self.counter[threading.get_ident()] += 1
        start = monotonic()
        out = execute(sql, params, many, context)
        duration = monotonic() - start
        if self.log_all:
            logger.debug('Query: %s, params: %s', sql, params)
            logger.debug('Query took: %.2f s', duration)
        return out


class QueryLoggingMiddleware:
    """
    Uses `QueryCounter` to wrap all database call and count the number of queries
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.qc = QueryCounter()

    def __call__(self, request):
        tid = threading.get_ident()
        start = self.qc.counter[tid]
        with connection.execute_wrapper(self.qc):
            response = self.get_response(request)
            response['X-Django-Query-Count'] = self.qc.counter[tid] - start
            return response
