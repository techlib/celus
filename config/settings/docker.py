import os

from .staging import DATABASES
from .staging import CACHES
from .staging import *  # noqa


ALLOWED_HOSTS = ["*"]

DATABASES["default"]["NAME"] = os.environ.get("POSTGRES_DB", "celus")
DATABASES["default"]["USER"] = os.environ.get("POSTGRES_USER", "celus")
DATABASES["default"]["PASSWORD"] = os.environ.get("POSTGRES_PASSWORD", "celus")
DATABASES["default"]["HOST"] = os.environ.get("POSTGRES_HOST", "celus-postgres")
DATABASES["default"]["PORT"] = os.environ.get("POSTGRES_PORT", "5432")

CACHES["default"]["LOCATION"] = os.environ.get("REDIS_LOCATION", "redis://celus-redis:6379/1")

AUTHENTICATION_BACKENDS = [
    # 'apps.core.auth.EDUIdAuthenticationBackend',
    "django.contrib.auth.backends.ModelBackend",
]

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://celus-redis:6379")
