from .base import *

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration

ALLOWED_HOSTS = ['stats.czechelib.cz']
LIVE_ERMS_AUTHENTICATION = True

DEBUG = False

STATIC_ROOT = '/var/www/celus/static/'
MEDIA_ROOT = '/var/www/celus/media/'

ADMINS = (("Beda Kosata", "beda@bigdigdata.com"),)

EMAIL_HOST = 'smtp.ntkcz.cz'
SERVER_EMAIL = 'admin@stats.czechelib.cz'


# sentry
if SENTRY_URL:
    sentry_sdk.init(
        dsn=SENTRY_URL,
        integrations=[DjangoIntegration(), CeleryIntegration(), RedisIntegration()],
        send_default_pii=True,
    )
