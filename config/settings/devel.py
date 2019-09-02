from .base import *

INSTALLED_APPS += ['debug_toolbar']
INSTALLED_APPS.insert(4, 'livereload')  # it must be before staticfiles
# LIVE_ERMS_AUTHENTICATION = True

MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'livereload.middleware.LiveReloadScript',
    'querycount.middleware.QueryCountMiddleware',
]

# livereload
LIVERELOAD_PORT = 35563
# debug toolbar
INTERNAL_IPS = ['127.0.0.1']
