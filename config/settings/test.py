import os

from .base import *  # noqa
from .base import CACHES, DATABASES

LIVE_ERMS_AUTHENTICATION = False

DATABASES["default"]["NAME"] = os.environ.get("POSTGRES_DB", "celus")
DATABASES["default"]["USER"] = os.environ.get("POSTGRES_USER", "celus")
DATABASES["default"]["PASSWORD"] = os.environ.get("POSTGRES_PASSWORD", "celus")
DATABASES["default"]["HOST"] = os.environ.get("POSTGRES_HOST", "127.0.0.1")

CACHES["default"]["LOCATION"] = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/1")

ALLOW_USER_CREATED_PLATFORMS = True
ALLOW_USER_REGISTRATION = True

DISABLE_CACHALOT = True
