"""
Django settings for Celus project.

Generated by 'django-admin startproject' using Django 2.2.1.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""
from datetime import timedelta
from pathlib import Path
from distutils.util import strtobool
import os
import sys

from celery.schedules import schedule, crontab

from .json_settings import load_secret_settings_json_file


BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR / 'apps'))

SECRET_KEY = '----REPLACE ME------'

DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'modeltranslation',  # must be before admin
    'django.contrib.admin',
    'rest_framework',
    'rest_framework.authtoken',
    'django_celery_results',
    'mptt',
    'reversion',
    'rest_auth',
    'django.contrib.sites',
    'rest_auth.registration',
    'core.apps.CoreConfig',
    'publications.apps.PublicationsConfig',
    'logs.apps.LogsConfig',
    'organizations.apps.OrganizationsConfig',
    'sushi.apps.SushiConfig',
    'charts.apps.ChartsConfig',
    'annotations.apps.AnnotationsConfig',
    'cost.apps.CostConfig',
    'activity.apps.ActivityConfig',
    'api.apps.ApiConfig',
    'rest_pandas',
    'error_report',
    'cachalot',
    'django_prometheus',
    # allauth is at the end so that we can easily override its templates
    'allauth',
    'allauth.socialaccount',
    'allauth.account',
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.EDUIdHeaderMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'error_report.middleware.ExceptionProcessor',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
    'apps.core.auth.EDUIdAuthenticationBackend',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django_prometheus.db.backends.postgresql',
        'NAME': 'celus',
        'USER': 'celus',
        'PASSWORD': '--REPLACE ME--',  # should be replaced later with data from secret json
        'HOST': '127.0.0.1',
        'PORT': '5432',
        'ATOMIC_REQUESTS': True,
    }
}


# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# Custom user model
AUTH_USER_MODEL = 'core.User'


# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Europe/Prague'
USE_I18N = True
USE_L10N = True
USE_TZ = True

gettext = lambda s: s
LANGUAGES = (
    ('en', gettext('English')),
    ('cs', gettext('Czech')),
)


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = str(BASE_DIR / 'media/')

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
STATIC_ROOT = BASE_DIR / "static_compiled"

# Email
ADMINS = (("Beda Kosata", "beda@bigdigdata.com"),)
EMAIL_SUBJECT_PREFIX = '[Stats] '

# REST framework

REST_FRAMEWORK = {
    'COERCE_DECIMAL_TO_STRING': False,
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
        'rest_pandas.renderers.PandasCSVRenderer',
        'rest_pandas.renderers.PandasExcelRenderer',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': ['core.authentication.SessionAuthentication401',]
    # 'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    # 'PAGE_SIZE': 10
}

# CACHE
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        # "BACKEND": "django_prometheus.cache.backends.redis",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "COMPRESSOR": "django_redis.compressors.lz4.Lz4Compressor",
        },
        "VERSION": 1,
    }
}

# Cachalot related settings
CACHALOT_ONLY_CACHABLE_TABLES = frozenset(
    (
        'charts_chartdefinition',
        'charts_dimensionfilter',
        'charts_reportdataview',
        'charts_reportviewtocharttype',
        'logs_accesslog',
        'logs_dimension',
        'logs_dimensiontext',
        'logs_interestgroup',
        'logs_metric',
        'logs_organizationplatform',
        'logs_reportinterestmetric',
        'logs_reporttype',
        'logs_reporttypetodimension',
        'organizations_organization',
        'organizations_userorganization',
        'publications_platform',
        'publications_platforminterestreport',
        'publications_platformtitle',
        'publications_title',
        'sushi_counterreporttype',
    )
)
# CACHALOT_UNCACHABLE_TABLES = frozenset(('django_migrations',))

# Celery
CELERY_RESULT_BACKEND = 'django-db'
CELERY_BROKER_URL = 'redis://localhost'
CELERY_TIMEZONE = TIME_ZONE

# Note about priorities - it is not clear from the Celery documentation, but from my experiments
# it looks like:
# - 0 means "higher" priority - it gets processed first
#   9 is the "lowest" priority - gets processed last
# - default priority is 0 (or 1 or 2 - these end up in the same list)

CELERY_BROKER_TRANSPORT_OPTIONS = {
    'queue_order_strategy': 'priority',
}

CELERY_TASK_ROUTES = {
    'logs.tasks.sync_interest_task': {'queue': 'interest'},
    'logs.tasks.recompute_interest_by_batch_task': {'queue': 'interest'},
    'sushi.tasks.retry_queued_attempts_task': {'queue': 'sushi'},
    'sushi.tasks.run_sushi_fetch_attempt_task': {'queue': 'sushi'},
    'sushi.tasks.fetch_new_sushi_data_task': {'queue': 'sushi'},
    'sushi.tasks.fetch_new_sushi_data_for_credentials_task': {'queue': 'sushi'},
    'logs.tasks.import_new_sushi_attempts_task': {'queue': 'import'},
    'logs.tasks.smart_interest_sync_task': {'queue': 'interest'},
    'logs.tasks.sync_materialized_reports_task': {'queue': 'interest'},
    'core.tasks.test': {'queue': 'normal'},
}

CELERY_BEAT_SCHEDULE = {
    'smart_interest_sync_task': {
        'task': 'logs.tasks.smart_interest_sync_task',
        'schedule': schedule(run_every=timedelta(minutes=10)),
    },
    'sync_materialized_reports_task': {
        'task': 'logs.tasks.sync_materialized_reports_task',
        'schedule': schedule(run_every=timedelta(minutes=7)),
    },
    'retry_queued_attempts_task': {
        'task': 'sushi.tasks.retry_queued_attempts_task',
        'schedule': schedule(run_every=timedelta(minutes=30)),
    },
    'import_new_sushi_attempts_task': {
        'task': 'logs.tasks.import_new_sushi_attempts_task',
        'schedule': schedule(run_every=timedelta(minutes=5)),
    },
    'fetch_new_sushi_data_task': {
        'task': 'sushi.tasks.fetch_new_sushi_data_task',
        'schedule': crontab(minute=13, hour=3),  # every day at 3:13
    },
    'erms_sync_platforms_task': {
        'task': 'publications.tasks.erms_sync_platforms_task',
        'schedule': schedule(run_every=timedelta(minutes=30)),
    },
    'erms_sync_organizations_task': {
        'task': 'organizations.tasks.erms_sync_organizations_task',
        'schedule': schedule(run_every=timedelta(days=1)),
    },
    'erms_sync_users_and_identities_task': {
        'task': 'core.tasks.erms_sync_users_and_identities_task',
        'schedule': schedule(run_every=timedelta(minutes=30)),
    },
}


# ERMS related stuff
ERMS_API_URL = "https://erms.czechelib.cz/api/"
EDUID_IDENTITY_HEADER = 'HTTP_X_IDENTITY'
MASTER_ORGANIZATIONS = ['NTK-61387142-CEL']  # organizations whose users should have access to all
# should we try to authenticate against ERMS before trying local data?
LIVE_ERMS_AUTHENTICATION = False
QUEUED_SUSHI_MAX_RETRY_COUNT = 5  # how many times max should we retry queued attempts
SUSHI_ATTEMPT_LAST_DATE = '2017-01'  # default date where to end fetching sushi data
REFERENCE_CURRENCY = 'CZK'  # this is the currency used for price calculation

# Celus features configuration
CONSORTIAL_INSTALLATION = True  # is this installation intended for one consortium
ALLOW_MANUAL_UPLOAD = True

# use authentication and registration
# should users be allowed to create accounts themselves
ALLOW_USER_REGISTRATION = False
# social authentication providers
SOCIAL_ACCOUNTS_SUPPORTED = []
SITE_ID = 1
# allauth config
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_VERIFICATION = "optional"  # send verification email, but not required for login
ACCOUNT_EMAIL_CONFIRMATION_HMAC = False  # Confirmation will be stored in db
ACCOUNT_ADAPTER = 'core.account.CelusAccountAdapter'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'level': 'DEBUG', 'class': 'logging.StreamHandler',},},
    'loggers': {
        'django.db': {'level': 'INFO',},
        'pycounter': {'level': 'INFO',},
        'requests': {'level': 'INFO',},
    },
    'root': {'level': 'DEBUG', 'handlers': ['console'],},
}

# hopefully temporary hacks
SILENCED_SYSTEM_CHECKS = []

# This loads the secret key and potentially other secret settings from a JSON file
# it must be kept here, otherwise the settings will be missing
secrets = load_secret_settings_json_file(BASE_DIR / 'config/settings/secret_settings.json')
for key in ("SECRET_KEY",):
    locals()[key] = secrets[key]
# optional keys
for key in ("ERMS_API_URL",):
    if key in secrets:
        locals()[key] = secrets[key]

DATABASES['default']['PASSWORD'] = secrets['DB_PASSWORD']

EXPORTED_SETTINGS = [
    'REFERENCE_CURRENCY',
    'AUTHENTICATION_BACKENDS',
    'ALLOW_USER_REGISTRATION',
    'SOCIAL_ACCOUNTS_SUPPORTED',
    'CONSORTIAL_INSTALLATION',
    'ALLOW_MANUAL_UPLOAD',
]

# Need to disable prometheus migrations when collecting static without DB
# see https://github.com/korfuri/django-prometheus/issues/34
PROMETHEUS_EXPORT_MIGRATIONS = strtobool(os.environ.get('PROMETHEUS_EXPORT_MIGRATIONS', '1'))
