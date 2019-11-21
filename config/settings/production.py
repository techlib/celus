from .base import *

ALLOWED_HOSTS = ['stats.czechelib.cz']
LIVE_ERMS_AUTHENTICATION = True

DEBUG = False

STATIC_ROOT = '/var/www/html/stats/static/'
MEDIA_ROOT = '/var/www/html/stats/media/'

ADMINS = (
    ("Beda Kosata", "beda@bigdigdata.com"),
)

EMAIL_HOST = 'smtp.ntkcz.cz'
SERVER_EMAIL = 'admin@stats.czechelib.cz'
