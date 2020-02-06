from .base import *

DATABASES['default']['USER'] = 'celus_demo'
DATABASES['default']['NAME'] = 'celus_demo'
DATABASES['default']['HOST'] = 'db.i.bigdigdata.com'

ALLOWED_HOSTS = ['celusdemo.bigdigdata.com', 'demo.celus.net']
LIVE_ERMS_AUTHENTICATION = False

DEBUG = False

STATIC_ROOT = '/var/www/celus/static/'
MEDIA_ROOT = '/var/www/celus/media/'

ADMINS = (
    ("Beda Kosata", "beda@bigdigdata.com"),
)

EMAIL_HOST = 'smtp.ntkcz.cz'
SERVER_EMAIL = 'admin@stats.czechelib.cz'
