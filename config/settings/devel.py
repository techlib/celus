import os

from .base import *

ALLOWED_HOSTS = ['*']

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

INSTALLED_APPS += ['debug_toolbar']

MIDDLEWARE = (
    MIDDLEWARE[:-1]
    + [
        'debug_toolbar.middleware.DebugToolbarMiddleware',
        'querycount.middleware.QueryCountMiddleware',
    ]
    + MIDDLEWARE[-1:]
)

CACHE_MIDDLEWARE_SECONDS = 1


DEBUG_TOOLBAR_PANELS = [
    'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
]

if not DISABLE_CACHALOT:
    DEBUG_TOOLBAR_PANELS.append('cachalot.panels.CachalotPanel')

DEBUG_TOOLBAR_PANELS += [
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.logging.LoggingPanel',
    'debug_toolbar.panels.redirects.RedirectsPanel',
]

# debug toolbar
INTERNAL_IPS = ['127.0.0.1']


# disable most periodic celery tasks
CELERY_BEAT_SCHEDULE = {
    'sync_interest_task': {
        'task': 'logs.tasks.sync_interest_task',
        'schedule': schedule(run_every=timedelta(days=1)),
    },
    'find_and_renew_first_due_cached_query_task': {
        'task': 'recache.tasks.find_and_renew_first_due_cached_query_task',
        'schedule': schedule(run_every=timedelta(minutes=3)),
    },
}


QUERYCOUNT = {
    'DISPLAY_DUPLICATES': 5,
}
