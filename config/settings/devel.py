from .base import *

INSTALLED_APPS += ['debug_toolbar']
INSTALLED_APPS.insert(4, 'livereload')  # it must be before staticfiles
LIVE_ERMS_AUTHENTICATION = True

MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'livereload.middleware.LiveReloadScript',
    'querycount.middleware.QueryCountMiddleware',
]

DATABASES['default']['NAME'] = 'ntk_stats'
CACHE_MIDDLEWARE_SECONDS = 1


DEBUG_TOOLBAR_PANELS = [
    'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'cachalot.panels.CachalotPanel',
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.logging.LoggingPanel',
    'debug_toolbar.panels.redirects.RedirectsPanel',
]

# livereload
LIVERELOAD_PORT = 35563
# debug toolbar
INTERNAL_IPS = ['127.0.0.1']


# disable most periodic celery tasks
CELERY_BEAT_SCHEDULE = {
    'sync_interest_task': {
        'task': 'logs.tasks.sync_interest_task',
        'schedule': schedule(run_every=timedelta(days=1)),
    },
}
