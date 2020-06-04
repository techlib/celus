from .base import *

DATABASES['default']['USER'] = 'celus_demo'
DATABASES['default']['NAME'] = 'celus_demo'
DATABASES['default']['HOST'] = 'db.i.bigdigdata.com'
MASTER_ORGANIZATIONS = [
    'NTK-61387142-CEL',
    'GMJ-9379',
]  # organizations whose users should have access to all

ALLOWED_HOSTS = ['celusdemo.bigdigdata.com', 'demo.celus.net']
LIVE_ERMS_AUTHENTICATION = False

DEBUG = False

STATIC_ROOT = '/var/www/celus/static/'
MEDIA_ROOT = '/var/www/celus/media/'

ADMINS = (("Beda Kosata", "beda@bigdigdata.com"),)

EMAIL_HOST = 'smtp.ntkcz.cz'
SERVER_EMAIL = 'admin@stats.czechelib.cz'

# reduce the amount of celery beat tasks for demo
CELERY_BEAT_SCHEDULE = {
    'smart_interest_sync_task': {
        'task': 'logs.tasks.smart_interest_sync_task',
        'schedule': schedule(run_every=timedelta(minutes=10)),
    },
    'import_new_sushi_attempts_task': {
        'task': 'logs.tasks.import_new_sushi_attempts_task',
        'schedule': schedule(run_every=timedelta(minutes=5)),
    },
}
