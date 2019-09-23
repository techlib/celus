from .base import *

INSTALLED_APPS += ['debug_toolbar']
INSTALLED_APPS.insert(4, 'livereload')  # it must be before staticfiles
# LIVE_ERMS_AUTHENTICATION = True

MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'livereload.middleware.LiveReloadScript',
    'querycount.middleware.QueryCountMiddleware',
]

DATABASES['default']['NAME'] = 'ntk_stats3'

# livereload
LIVERELOAD_PORT = 35563
# debug toolbar
INTERNAL_IPS = ['127.0.0.1']


# disable most periodic celery tasks
CELERY_BEAT_SCHEDULE = {
    'sync_interest_task': {
        'task': 'logs.tasks.sync_interest_task',
        'schedule': schedule(run_every=timedelta(minutes=5)),
    },
}
