import ipaddress
import logging
import pickle
import time
import urllib

import redis
from core.tasks import async_mail_admins
from django.conf import settings
from requestlogs.storages import BaseStorage

logger = logging.getLogger(__name__)


class RedisBufferStorage(BaseStorage):
    def store(self, entry):
        try:
            start = time.time()
            r = redis.Redis(
                host=settings.REQUEST_LOGGING_REDIS_HOST,
                port=settings.REQUEST_LOGGING_REDIS_PORT,
                db=settings.REQUEST_LOGGING_REDIS_DB,
            )
            data = entry_to_dict(entry)
        except Exception as e:
            logger.error(f'Error creating request log: {e}')
            async_mail_admins.delay(
                'Error creating request log', f'Error: {str(e)}\nType: {type(e)}'
            )
            return
        try:
            r.rpush(settings.REQUEST_LOGGING_REDIS_KEY, pickle.dumps(data))
            logger.debug('Request logging took %.2f ms', 1000 * (time.time() - start))
        except Exception as e:
            logger.error(f'Error storing request log: {e}')
            async_mail_admins.delay('Error storing request log', f'Error: {e}\n\nData: {str(data)}')


def entry_to_dict(entry):
    ip_address = ipaddress.ip_address(entry.ip_address)
    # request is a list of tuples
    request_info = entry.request
    response_info = entry.response
    user = entry.django_request.user if hasattr(entry.django_request, 'user') else None
    real_user = (
        entry.django_request.real_user if hasattr(entry.django_request, 'real_user') else None
    )
    impersonified = bool(real_user and user and not user.is_anonymous and real_user.pk != user.pk)
    request_path = request_info.path
    referer_url = entry.django_request.META.get('HTTP_REFERER', '')
    if referer_url:
        ref_url = urllib.parse.urlparse(referer_url)
        ref_path = ref_url.path
        # values are lists, but we want to store them as single value if possible
        ref_query_params = {
            k: v[0] if len(v) == 1 else str(v)
            for k, v in urllib.parse.parse_qs(ref_url.query, keep_blank_values=True).items()
        }
    else:
        ref_path = ''
        ref_query_params = {}

    # request data can be almost anything, so we store it as a string
    try:
        request_data = getattr(request_info, 'data', None)
    except TypeError:
        request_data = getattr(request_info.request, 'data', None)
    request_data = str(request_data) if request_data else ''
    # streaming responses do not have 'content' attribute
    response_size = (
        len(response_info.response.content) if hasattr(response_info.response, 'content') else 0
    )
    # request size is taken from the Content-Length header, not by actually measuring it
    request_size = entry.django_request.headers.get('Content-Length', 0) or 0
    try:
        request_size = int(request_size)
    except ValueError:
        request_size = 0
    request_content_type = entry.django_request.headers.get('Content-Type', '')
    rm = entry.django_request.resolver_match
    request_view = rm.func.__name__ if rm else ''
    request_url_name = (rm.url_name or '') if rm else ''
    request_view_args = [str(arg) for arg in rm.args] if rm else []
    request_view_kwargs = {k: str(v) for k, v in rm.kwargs.items()} if rm else {}
    return dict(
        hostname=entry.django_request.META['SERVER_NAME'],
        db_server=settings.DATABASES['default']['HOST'],
        clickhouse_db_server=settings.CLICKHOUSE_HOST,
        timestamp=entry.timestamp,
        ipv4=ip_address if isinstance(ip_address, ipaddress.IPv4Address) else '',
        ipv6=ip_address if isinstance(ip_address, ipaddress.IPv6Address) else '',
        request_method=request_info.method,
        request_path=request_path,
        request_view=request_view,
        request_url_name=request_url_name,
        request_view_args=request_view_args,
        request_view_kwargs=request_view_kwargs,
        request_query_params={k: str(v) for k, v in request_info.query_params.items()},
        request_data=request_data,
        request_headers=request_info.request_headers,
        request_content_type=request_content_type,
        ref_path=ref_path,
        ref_query_params=ref_query_params,
        response_status_code=response_info.status_code,
        user_id=user.pk if user and not user.is_anonymous else 0,
        user_email=user.email if user and not user.is_anonymous else '',
        user_username=user.username if user and not user.is_anonymous else '',
        user_is_staff=user.is_staff if user else False,
        user_is_superuser=user.is_superuser if user else False,
        user_is_active=user.is_active if user else False,
        real_user_id=real_user.pk if real_user and not real_user.is_anonymous else 0,
        real_user_email=real_user.email if real_user and not real_user.is_anonymous else '',
        real_user_username=real_user.username if real_user and not real_user.is_anonymous else '',
        impersonified=impersonified,
        debug=settings.DEBUG,
        celus_version=settings.CELUS_VERSION,
        celus_git_hash=settings.SENTRY_RELEASE,
        clickhouse_query_active=entry.django_request.USE_CLICKHOUSE
        if hasattr(entry.django_request, 'USE_CLICKHOUSE')
        else False,
        query_count_django=response_info.response.headers.get('X-Django-Query-Count', 0),
        query_count_clickhouse=response_info.response.headers.get('X-Clickhouse-Query-Count', 0),
        request_size=request_size,
        response_size=response_size,
        execution_time=1000 * entry.execution_time.total_seconds(),
    )
