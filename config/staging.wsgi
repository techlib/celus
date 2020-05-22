import os

from django.core.wsgi import get_wsgi_application

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.staging'
os.environ['prometheus_multiproc_dir'] = '/tmp/django_prometheus/'

application = get_wsgi_application()
