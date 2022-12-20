import os

# we need to disable cachalot through environment because this changes caused by this setting
# are applied in config.settings.base and it does not help overriding them later on
os.environ['DISABLE_CACHALOT'] = 'true'

from .base import *  # noqa

LIVE_ERMS_AUTHENTICATION = False

DATABASES["default"]["NAME"] = config("POSTGRES_DB", "celus")  # noqa F405
DATABASES["default"]["USER"] = config("POSTGRES_USER", "celus")  # noqa F405
DATABASES["default"]["PASSWORD"] = config("POSTGRES_PASSWORD", "celus")  # noqa F405
DATABASES["default"]["HOST"] = config("POSTGRES_HOST", "127.0.0.1")  # noqa F405

CACHES["default"]["LOCATION"] = config("REDIS_URL", "redis://127.0.0.1:6379/1")  # noqa F405
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost')  # noqa F405

ALLOW_USER_CREATED_PLATFORMS = True
ALLOW_USER_REGISTRATION = True

CLICKHOUSE_SYNC_ACTIVE = config('CLICKHOUSE_SYNC_ACTIVE', cast=bool, default=True)  # noqa F405
CLICKHOUSE_QUERY_ACTIVE = config(  # noqa F405
    'CLICKHOUSE_QUERY_ACTIVE', cast=bool, default=CLICKHOUSE_SYNC_ACTIVE
)
