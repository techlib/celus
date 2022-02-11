import os

# we need to disable cachalot through environment because this changes caused by this setting
# are applied in config.settings.base and it does not help overriding them later on
os.environ['DISABLE_CACHALOT'] = 'true'

from .base import *  # noqa

LIVE_ERMS_AUTHENTICATION = False

DATABASES["default"]["NAME"] = os.environ.get("POSTGRES_DB", "celus")
DATABASES["default"]["USER"] = os.environ.get("POSTGRES_USER", "celus")
DATABASES["default"]["PASSWORD"] = os.environ.get("POSTGRES_PASSWORD", "celus")
DATABASES["default"]["HOST"] = os.environ.get("POSTGRES_HOST", "127.0.0.1")

CACHES["default"]["LOCATION"] = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/1")

ALLOW_USER_CREATED_PLATFORMS = True
ALLOW_USER_REGISTRATION = True

CLICKHOUSE_SYNC_ACTIVE = config('CLICKHOUSE_SYNC_ACTIVE', cast=bool, default=True)
CLICKHOUSE_QUERY_ACTIVE = config(
    'CLICKHOUSE_QUERY_ACTIVE', cast=bool, default=CLICKHOUSE_SYNC_ACTIVE
)
