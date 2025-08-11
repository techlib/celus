import os

# we need to disable cachalot through environment because this changes caused by this setting
# are applied in config.settings.base and it does not help overriding them later on
os.environ["DISABLE_CACHALOT"] = "true"

from .base import *  # noqa

TESTING = True
LIVE_ERMS_AUTHENTICATION = False
ALLOW_EDUID_LOGIN = True  # some tests rely on eduid login being enabled
ACCOUNT_RATE_LIMITS = False  # otherwise default rate limit will block emails in tests

DATABASES["default"]["NAME"] = config("POSTGRES_DB", "celus")  # noqa F405
DATABASES["default"]["USER"] = config("POSTGRES_USER", "celus")  # noqa F405
DATABASES["default"]["PASSWORD"] = config("POSTGRES_PASSWORD", "celus")  # noqa F405
DATABASES["default"]["HOST"] = config("POSTGRES_HOST", "127.0.0.1")  # noqa F405

POSTGRES_FOR_CLICKHOUSE = config("POSTGRES_FOR_CLICKHOUSE", default=DATABASES["default"]["HOST"])  # noqa F405

CACHES["default"]["LOCATION"] = config("REDIS_URL", "redis://127.0.0.1:6379/1")  # noqa F405
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost")  # noqa F405

ALLOW_USER_CREATED_PLATFORMS = True
ALLOW_USER_REGISTRATION = True
ALLOW_USER_MANAGEMENT = True

CLICKHOUSE_SYNC_ACTIVE = config("CLICKHOUSE_SYNC_ACTIVE", cast=bool, default=True)  # noqa F405
CLICKHOUSE_QUERY_ACTIVE = config(  # noqa F405
    "CLICKHOUSE_QUERY_ACTIVE", cast=bool, default=CLICKHOUSE_SYNC_ACTIVE
)

LOGGING["handlers"]["mail_admins"][  # noqa F405
    "email_backend"
] = "django.core.mail.backends.console.EmailBackend"

# Make enable OTP otherwise otp endpoints are missing in the tests
OTP_ENABLED = True
OTP_CREATE_EMAIL_DEVICES = False
