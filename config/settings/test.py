import os

from decouple import Csv, config

# we need to disable cachalot through environment because this changes caused by this setting
# are applied in config.settings.base and it does not help overriding them later on
os.environ['DISABLE_CACHALOT'] = 'true'

from .base import *  # noqa

LIVE_ERMS_AUTHENTICATION = False

DATABASES["default"]["NAME"] = config("POSTGRES_DB", "celus")
DATABASES["default"]["USER"] = config("POSTGRES_USER", "celus")
DATABASES["default"]["PASSWORD"] = config("POSTGRES_PASSWORD", "celus")
DATABASES["default"]["HOST"] = config("POSTGRES_HOST", "127.0.0.1")

CACHES["default"]["LOCATION"] = config("REDIS_URL", "redis://127.0.0.1:6379/1")
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost')

ALLOW_USER_CREATED_PLATFORMS = True
ALLOW_USER_REGISTRATION = True

CLICKHOUSE_SYNC_ACTIVE = config('CLICKHOUSE_SYNC_ACTIVE', cast=bool, default=True)
CLICKHOUSE_QUERY_ACTIVE = config(
    'CLICKHOUSE_QUERY_ACTIVE', cast=bool, default=CLICKHOUSE_SYNC_ACTIVE
)
