import logging
import pickle
import time
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils.timezone import now
from django_celery_results.models import TaskResult

from core.logic.util import this_celus_domain

logger = logging.getLogger(__name__)


# async_mail_admins is used inside the error handling code,
# so we need to ignore it to avoid infinite recursion
IGNORED_TASKS = ["async_mail_admins"]


def create_celery_task_log_dict(
    sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kw
) -> dict:
    try:
        task_obj = TaskResult.objects.get(task_id=task_id)
    except TaskResult.DoesNotExist:
        task_obj = None

    duration = (
        (task_obj.date_done - task_obj.date_created)
        if task_obj and task_obj.date_done
        else timedelta(seconds=0)
    )

    # get the django query count from the cache
    # it was saved by the `logged_task` decorator if used
    query_count_django = cache.get(f"celery_task_query_count_{task_id}", 0)
    cache.delete(f"celery_task_query_count_{task_id}")
    # the same for clickhouse
    clickhouse_query_count = cache.get(f"celery_task_ch_query_count_{task_id}", 0)
    cache.delete(f"celery_task_ch_query_count_{task_id}")

    return {
        "hostname": this_celus_domain(),
        "db_server": settings.DATABASES["default"]["HOST"],
        "clickhouse_db_server": settings.CLICKHOUSE_HOST,
        "timestamp": task_obj.date_created if task_obj else now(),
        "debug": settings.DEBUG,
        "celus_version": settings.CELUS_VERSION,
        "celus_git_hash": settings.SENTRY_RELEASE,
        "clickhouse_query_active": settings.CLICKHOUSE_QUERY_ACTIVE,
        "query_count_django": query_count_django,
        "query_count_clickhouse": clickhouse_query_count,
        "execution_time": duration.total_seconds() * 1000,
        "task_name": task.__name__,
        "task_args": [str(arg) for arg in args] if args else [],
        "task_kwargs": {k: str(v) for k, v in kwargs.items()} if kwargs else {},
        "status": state,
    }


def celery_task_log(
    sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kw
):
    """
    Creates a log entry for a celery task and pushes it to redis from where it
    will be picked up by a celery task and inserted into clickhouse later on.
    """
    if task.__name__ in settings.CELERY_LOGGING_IGNORED_TASKS or task.__name__ in IGNORED_TASKS:
        return

    data = create_celery_task_log_dict(
        sender=sender,
        task_id=task_id,
        task=task,
        args=args,
        kwargs=kwargs,
        retval=retval,
        state=state,
        **kw,
    )

    try:
        start = time.time()
        # Celery logging shares the same infrastructure as request logging, so we use the same
        # redis settings. The only difference is that we use a different redis key as shown below.
        import redis  # noqa - slow import

        r = redis.Redis(
            host=settings.REQUEST_LOGGING_REDIS_HOST,
            port=settings.REQUEST_LOGGING_REDIS_PORT,
            db=settings.REQUEST_LOGGING_REDIS_DB,
        )
    except Exception as e:
        from core.tasks import async_mail_admins

        logger.error(f"Error creating celery log: {e}")
        async_mail_admins.delay("Error creating request log", f"Error: {str(e)}\nType: {type(e)}")
        return
    try:
        r.rpush(settings.CELERY_LOGGING_REDIS_KEY, pickle.dumps(data))
        logger.debug("Celery task logging took %.2f ms", 1000 * (time.time() - start))
    except Exception as e:
        from core.tasks import async_mail_admins

        logger.error(f"Error storing celery log: {e}")
        async_mail_admins.delay("Error storing celery log", f"Error: {e}\n\nData: {str(data)}")
