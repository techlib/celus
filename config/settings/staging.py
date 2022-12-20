from .base import *  # noqa F403 F401

ALLOWED_HOSTS = ['stats.test.czechelib.cz']
LIVE_ERMS_AUTHENTICATION = True

DEBUG = False

STATIC_ROOT = '/var/www/celus/static/'
MEDIA_ROOT = '/var/www/celus/media/'

ADMINS = (("Beda Kosata", "beda@bigdigdata.com"),)

EMAIL_HOST = 'smtp.ntkcz.cz'
SERVER_EMAIL = 'admin@stats.test.czechelib.cz'
