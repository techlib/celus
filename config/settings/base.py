"""
Django settings for Celus project.

Generated by 'django-admin startproject' using Django 2.2.1.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""
import sys
import warnings
from datetime import timedelta
from pathlib import Path

import sentry_sdk
from celery.schedules import crontab, schedule
from decouple import Choices, Csv, config
from django.core.exceptions import ImproperlyConfigured
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import ignore_logger
from sentry_sdk.integrations.redis import RedisIntegration

from . import get_version

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR / 'apps'))

USES_ERMS = config('USES_ERMS', cast=bool, default=False)

CELUS_VERSION = get_version(BASE_DIR)

# Application definition

INSTALLED_APPS = [
    # `core` is here before `auth` because it overrides some templates in registration
    'core.apps.CoreConfig',
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
    'dj_rest_auth',
    'django.contrib.sites',
    'dj_rest_auth.registration',
    'publications.apps.PublicationsConfig',
    'logs.apps.LogsConfig',
    'organizations.apps.OrganizationsConfig',
    'sushi.apps.SushiConfig',
    'charts.apps.ChartsConfig',
    'annotations.apps.AnnotationsConfig',
    'scheduler.apps.SchedulerConfig',
    'cost.apps.CostConfig',
    'activity.apps.ActivityConfig',
    'deployment.apps.DeploymentConfig',
    'api.apps.ApiConfig',
    'recache.apps.RecacheConfig',
    'knowledgebase.apps.KnowledgebaseConfig',
    'nibbler.apps.NibblerConfig',
    'export.apps.ExportConfig',
    'tags.apps.TagsConfig',
    'releases.apps.ReleasesConfig',
    'rest_pandas',
    'django_prometheus',
    'import_export',
    'rest_framework_api_key',
    'django.contrib.postgres',
    'impersonate',
    'colorfield',
    # allauth is at the end so that we can easily override its templates
    'allauth',
    'allauth.socialaccount',
    'allauth.account',
]

DISABLE_CACHALOT = config('DISABLE_CACHALOT', cast=bool, default=False)
if not DISABLE_CACHALOT:
    INSTALLED_APPS.append('cachalot')
else:
    print('cachalot disabled', file=sys.stderr)

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.EDUIdHeaderMiddleware',
    'impersonate.middleware.ImpersonateMiddleware',  # should be place after auth middlewares
    'core.middleware.CelusVersionHeaderMiddleware',
    'core.middleware.ClickhouseIntegrationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'core.middleware.UserLanguageMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']

ALLOW_EMAIL_LOGIN = config('ALLOW_EMAIL_LOGIN', cast=bool, default=True)
if ALLOW_EMAIL_LOGIN:
    AUTHENTICATION_BACKENDS.append('allauth.account.auth_backends.AuthenticationBackend')

ALLOW_EDUID_LOGIN = config('ALLOW_EDUID_LOGIN', cast=bool, default=True)
if ALLOW_EDUID_LOGIN:
    AUTHENTICATION_BACKENDS.append('apps.core.auth.EDUIdAuthenticationBackend')


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
            ]
        },
    }
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django_prometheus.db.backends.postgresql',
        'NAME': config('DB_NAME', default='celus'),
        'USER': config('DB_USER', default='celus'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', cast=int, default=5432),
        'ATOMIC_REQUESTS': True,
    },
}

print(f'Using database: {DATABASES["default"]["NAME"]}', file=sys.stderr)

DB_NAME_OLD = config('DB_NAME_OLD', default='')
if DB_NAME_OLD:
    DATABASES['old'] = {
        'ENGINE': 'django_prometheus.db.backends.postgresql',
        'NAME': DB_NAME_OLD,
        'USER': config('DB_USER', default='celus'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', cast=int, default=5432),
        'ATOMIC_REQUESTS': True,
    }

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'


# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
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
AVAILABLE_LANGUAGES = (('en', gettext('English')), ('cs', gettext('Czech')))
MODELTRANSLATION_LANGUAGES = [code for code, lang in AVAILABLE_LANGUAGES]
used_languages = config('USED_LANGUAGES', default='en', cast=Csv())
LANGUAGES = [lang for lang in AVAILABLE_LANGUAGES if lang[0] in used_languages]
LOCALE_PATHS = [BASE_DIR / 'locale']

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = config('MEDIA_ROOT', default=str(BASE_DIR / 'media/'))

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
STATIC_ROOT = config('STATIC_ROOT', default=BASE_DIR / "static_compiled")


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
    'DEFAULT_AUTHENTICATION_CLASSES': ['core.authentication.SessionAuthentication401']
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
CACHALOT_DATABASES = ['default']
CACHALOT_ONLY_CACHABLE_TABLES = frozenset(
    (
        'charts_chartdefinition',
        'charts_dimensionfilter',
        'charts_reportdataview',
        'charts_reportviewtocharttype',
        'core_user',
        'logs_accesslog',
        'logs_dimension',
        'logs_dimensiontext',
        'logs_interestgroup',
        'logs_metric',
        'logs_organizationplatform',
        'logs_reportinterestmetric',
        'logs_reporttype',
        'logs_reporttypetodimension',
        'logs_reportmaterializationspec',
        'organizations_organization',
        'organizations_userorganization',
        'publications_platform',
        'publications_platforminterestreport',
        'publications_platformtitle',
        'publications_title',
        'sushi_counterreporttype',
        'tags_tag',
        'tags_tagclass',
        'tags_itemtag',
        'tags_titletag',
        'tags_organizationtag',
        'tags_platformtag',
    )
)
# CACHALOT_UNCACHABLE_TABLES = frozenset(('django_migrations',))

# Clickhouse integration
# should data be synced to clickhouse on write?
CLICKHOUSE_SYNC_ACTIVE = config('CLICKHOUSE_SYNC_ACTIVE', cast=bool, default=False)
# should data from clickhouse be used when answering queries?
CLICKHOUSE_QUERY_ACTIVE = config('CLICKHOUSE_QUERY_ACTIVE', cast=bool, default=False)
if CLICKHOUSE_QUERY_ACTIVE and not CLICKHOUSE_SYNC_ACTIVE:
    warnings.warn(
        'Having `CLICKHOUSE_QUERY_ACTIVE` without `CLICKHOUSE_SYNC_ACTIVE` is likely an '
        'error as the data will not be up to date in queries.'
    )
CLICKHOUSE_DB = config('CLICKHOUSE_DB', default='celus')
CLICKHOUSE_USER = config('CLICKHOUSE_USER', default='celus')
CLICKHOUSE_PASSWORD = config('CLICKHOUSE_PASSWORD', default='celus')
CLICKHOUSE_HOST = config('CLICKHOUSE_HOST', default='localhost')
CLICKHOUSE_PORT = config('CLICKHOUSE_PORT', default=9000, cast=int)
CLICKHOUSE_SECURE = config('CLICKHOUSE_SECURE', default=False, cast=bool)

# 256k chars is the default max limit of clickhouse query
# it can be increased by setting max_query_size in config.xml, so we make it configurable.
# It influences how many IDs may be passed to the clickhouse database in one "IN" query
CLICKHOUSE_QUERY_SIZE_LIMIT = config('CLICKHOUSE_QUERY_SIZE_LIMIT', default=250_000, cast=int)

print(
    f'Clickhouse db: {CLICKHOUSE_DB}; sync: {CLICKHOUSE_SYNC_ACTIVE}; '
    f'query: {CLICKHOUSE_QUERY_ACTIVE}',
    file=sys.stderr,
)


# Celery
CELERY_RESULT_BACKEND = 'django-db'
CELERY_BROKER_URL = 'redis://localhost'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True

# Note about priorities - it is not clear from the Celery documentation, but from my experiments
# it looks like:
# - 0 means "higher" priority - it gets processed first
#   9 is the "lowest" priority - gets processed last
# - default priority is 0 (or 1 or 2 - these end up in the same list)

CELERY_BROKER_TRANSPORT_OPTIONS = {'queue_order_strategy': 'priority'}

# default route in Celery is called 'celery'
CELERY_TASK_DEFAULT_QUEUE = 'celery'  # just making the default explicit
# in production, we remap this queue to the name 'normal', but here it should either be omitted
# or explicitly set to 'celery'
CELERY_TASK_ROUTES = {
    'core.tasks.empty_task_export': {'queue': 'export'},
    'core.tasks.test': {'queue': 'celery'},
    'export.tasks.process_flexible_export_task': {'queue': 'export'},
    'knowledgebase.tasks.sync_routes': {'queue': 'celery'},
    'knowledgebase.tasks.sync_route': {'queue': 'celery'},
    'knowledgebase.tasks.sync_platforms_with_knowledgebase_task': {'queue': 'celery'},
    'knowledgebase.tasks.sync_report_types_with_knowledgebase_task': {'queue': 'celery'},
    'logs.tasks.sync_interest_task': {'queue': 'interest'},
    'logs.tasks.recompute_interest_by_batch_task': {'queue': 'interest'},
    'logs.tasks.import_new_sushi_attempts_task': {'queue': 'import'},
    'logs.tasks.import_one_sushi_attempt_task': {'queue': 'import'},
    'logs.tasks.smart_interest_sync_task': {'queue': 'interest'},
    'logs.tasks.sync_materialized_reports_task': {'queue': 'interest'},
    'logs.tasks.process_outstanding_import_batch_sync_logs_task': {'queue': 'celery'},
    'logs.tasks.update_report_approx_record_count_task': {'queue': 'interest'},
    'logs.tasks.export_raw_data_task': {'queue': 'export'},
    'logs.tasks.prepare_preflight': {'queue': 'preflight'},
    'logs.tasks.import_manual_upload_data': {'queue': 'import'},
    'logs.tasks.prepare_preflights': {'queue': 'preflight'},
    'logs.tasks.reprocess_mdu_task': {'queue': 'import'},
    'logs.tasks.compare_db_with_clickhouse_task': {'queue': 'import'},
    'logs.tasks.compare_db_with_clickhouse_delayed_task': {'queue': 'celery'},
    'publications.tasks.clean_obsolete_platform_title_links_task': {'queue': 'interest'},
    'publications.tasks.merge_titles_task': {'queue': 'interest'},
    'scheduler.tasks.plan_schedulers_triggering': {'queue': 'sushi'},
    'scheduler.tasks.update_automatic_harvesting': {'queue': 'sushi'},
    'scheduler.tasks.trigger_scheduler': {'queue': 'sushi'},
    'export.tasks.delete_expired_flexible_data_exports_task': {'queue': 'celery'},
}

# FlexibleDataExport settings
EXPORT_DELETING_PERIOD = timedelta(days=config('EXPORT_DELETING_DAYS', cast=int, default=7))

CELERY_BEAT_SCHEDULE = {
    'smart_interest_sync_task': {
        'task': 'logs.tasks.smart_interest_sync_task',
        'schedule': schedule(run_every=timedelta(minutes=10)),
        'options': {'expires': 10 * 60},
    },
    'sync_materialized_reports_task': {
        'task': 'logs.tasks.sync_materialized_reports_task',
        'schedule': schedule(run_every=timedelta(minutes=7)),
        'options': {'expires': 7 * 60},
    },
    'import_new_sushi_attempts_task': {
        'task': 'logs.tasks.import_new_sushi_attempts_task',
        'schedule': schedule(run_every=timedelta(minutes=5)),
        'options': {'expires': 5 * 60},
    },
    'find_and_renew_first_due_cached_query_task': {
        'task': 'recache.tasks.find_and_renew_first_due_cached_query_task',
        'schedule': schedule(run_every=timedelta(minutes=29)),
        'options': {'expires': 29 * 60},
    },
    'scheduler_plan_fetching': {
        'task': 'scheduler.tasks.plan_schedulers_triggering',
        'schedule': schedule(run_every=timedelta(minutes=1)),
        'options': {'expires': 60},
    },
    'knowledgebase_sync_routes': {
        'task': 'knowledgebase.tasks.sync_routes',
        'schedule': schedule(run_every=timedelta(minutes=5)),
        'options': {'expires': 5 * 60},
    },
    'process_outstanding_import_batch_sync_logs_task': {
        'task': 'logs.tasks.process_outstanding_import_batch_sync_logs_task',
        'schedule': schedule(run_every=timedelta(minutes=7)),
        'options': {'expires': 7 * 60},
    },
    'mdu_prepare_preflights': {
        'task': 'logs.tasks.prepare_preflights',
        'schedule': schedule(run_every=timedelta(minutes=5)),
        'options': {'expires': 5 * 60},
    },
    'mdu_unstuck_manual_imports': {
        'task': 'logs.tasks.unstuck_import_manual_upload_data',
        'schedule': schedule(run_every=timedelta(minutes=5)),
        'options': {'expires': 5 * 60},
    },
    'empty_task_export': {
        'task': 'core.tasks.empty_task_export',
        'schedule': schedule(run_every=timedelta(minutes=8)),
        'options': {'expires': 8 * 60},
    },
    # crontab schedules - daily stuff
    'scheduler_update_automatic_harvesting': {
        'task': 'scheduler.tasks.update_automatic_harvesting',
        'schedule': crontab(minute=50, hour=23),  # every day at 23:50
        'options': {'expires': 24 * 60 * 60},
    },
    'clean_obsolete_platform_title_links': {
        'task': 'publications.tasks.clean_obsolete_platform_title_links_task',
        'schedule': crontab(hour=0, minute=13),  # every day at 0:13
        'options': {'expires': 24 * 60 * 60},
    },
    'merge_titles_task': {
        'task': 'publications.tasks.merge_titles_task',
        'schedule': crontab(hour=0, minute=37),  # every day at 0:37
        'options': {'expires': 24 * 60 * 60},
    },
    'update_report_approx_record_count_task': {
        'task': 'logs.tasks.update_report_approx_record_count_task',
        'schedule': crontab(hour=1, minute=13),  # every day at 1:13
        'options': {'expires': 24 * 60 * 60},
    },
    'remove_old_cached_queries_task': {
        'task': 'recache.tasks.remove_old_cached_queries_task',
        'schedule': crontab(minute=17, hour=2),  # every day at 2:17
        'options': {'expires': 24 * 60 * 60},
    },
    'sync_platforms_with_knowledgebase_task': {
        'task': 'knowledgebase.tasks.sync_platforms_with_knowledgebase_task',
        'schedule': crontab(minute=33, hour=2),  # every day at 2:33
        'options': {'expires': 24 * 60 * 60},
    },
    # 'sync_report_types_with_knowledgebase_task': {
    #    'task': 'knowledgebase.tasks.sync_report_types_with_knowledgebase_task',
    #    'schedule': crontab(minute=44, hour=3),  # every day at 2:33
    #    'options': {'expires': 24 * 60 * 60},
    # },
    'delete_expired_flexible_data_exports_task': {
        'task': 'export.tasks.delete_expired_flexible_data_exports_task',
        'schedule': crontab(hour=3, minute=0),  # every day at 3:00
        'options': {'expires': 24 * 60 * 60},
    },
}

# add ERMS related tasks
ERMS_CELERY_SCHEDULE = {
    'erms_sync_platforms_task': {
        'task': 'publications.tasks.erms_sync_platforms_task',
        'schedule': schedule(run_every=timedelta(minutes=30)),
        'options': {'expires': 30 * 60},
    },
    'erms_sync_organizations_task': {
        'task': 'organizations.tasks.erms_sync_organizations_task',
        'schedule': schedule(run_every=timedelta(days=1)),
        'options': {'expires': 24 * 60 * 60},
    },
    'erms_sync_users_and_identities_task': {
        'task': 'core.tasks.erms_sync_users_and_identities_task',
        'schedule': schedule(run_every=timedelta(minutes=30)),
        'options': {'expires': 30 * 60},
    },
}
if USES_ERMS:
    CELERY_BEAT_SCHEDULE.update(ERMS_CELERY_SCHEDULE)


# add clickhouse related tasks
CLICKHOUSE_CELERY_SCHEDULE = {
    'compare_db_with_clickhouse_delayed_task': {
        'task': 'logs.tasks.compare_db_with_clickhouse_delayed_task',
        'schedule': crontab(minute=0, hour=22),  # every day at 22:00
        'options': {'expires': 22 * 60 * 60},  # expires in 22 hours to leave room for random delays
    },
}
if CLICKHOUSE_SYNC_ACTIVE:
    CELERY_BEAT_SCHEDULE.update(CLICKHOUSE_CELERY_SCHEDULE)


# allauth config
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_VERIFICATION = "optional"  # send verification email, but not required for login
ACCOUNT_EMAIL_CONFIRMATION_HMAC = False  # Confirmation will be stored in db
ACCOUNT_ADAPTER = 'core.account.CelusAccountAdapter'


# impersonate
IMPERSONATE = {
    "CUSTOM_USER_QUERYSET": 'impersonate_api.permissions.users_impersonable',
    "CUSTOM_ALLOW": 'impersonate_api.permissions.check_allow_impersonate',
    "ADMIN_DELETE_PERMISSION": True,
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'level': 'DEBUG', 'class': 'logging.StreamHandler', 'formatter': 'colored'},
        'errorlog': {
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': BASE_DIR / 'error.log',
        },
        'mail_admins': {'level': 'ERROR', 'class': 'django.utils.log.AdminEmailHandler'},
    },
    'loggers': {
        'django.db': {'level': 'INFO'},
        'pycounter': {'level': 'INFO'},
        'requests': {'level': 'INFO'},
        'django': {'level': 'ERROR', 'handlers': ['errorlog', 'mail_admins'], 'propagate': True},
        'logs.logic.materialized_interest': {'level': 'INFO'},
        'postgres_copy': {'level': 'ERROR'},
        'django_cachalot': {'level': 'DEBUG'},
    },
    'formatters': {
        'colored': {'()': 'colorlog.ColoredFormatter', 'format': "%(log_color)s%(message)s"}
    },
    'root': {'level': 'DEBUG', 'handlers': ['console']},
}

# hopefully temporary hacks
SILENCED_SYSTEM_CHECKS = []

# instance configuration
# django stuff
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', cast=bool, default=False)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv(), default=[])

# other django stuff
MAILGUN_API_KEY = config('MAILGUN_API_KEY', default='')
if MAILGUN_API_KEY:
    # if we have the mailgun api key, we activate mailgun
    INSTALLED_APPS += ['anymail']
    EMAIL_BACKEND = 'anymail.backends.mailgun.EmailBackend'
    ANYMAIL = {
        'MAILGUN_API_KEY': MAILGUN_API_KEY,
        'MAILGUN_SENDER_DOMAIN': config('MAILGUN_SENDER_DOMAIN', default='mg.celus.net'),
        'MAILGUN_API_URL': config('MAILGUN_API_URL', default='https://api.eu.mailgun.net/v3'),
    }

# ERMS related stuff
ERMS_API_URL = config('ERMS_API_URL', default='https://erms.czechelib.cz/api/')
if ERMS_API_URL:
    from erms.api import ERMS, ERMSError

    try:
        ERMS.check_url(ERMS_API_URL)
    except ERMSError as e:
        raise ImproperlyConfigured("ERMS_API_URL") from e


EDUID_IDENTITY_HEADER = config('EDUID_IDENTITY_HEADER', default='HTTP_X_IDENTITY')
# organizations whose users should have access to all
MASTER_ORGANIZATIONS = config('MASTER_ORGANIZATIONS', cast=Csv(), default='NTK-61387142-CEL')
# should we try to authenticate against ERMS before trying local data?
LIVE_ERMS_AUTHENTICATION = config('LIVE_ERMS_AUTHENTICATION', cast=bool, default=USES_ERMS)
# how many times max should we retry queued attempts
QUEUED_SUSHI_MAX_RETRY_COUNT = config('QUEUED_SUSHI_MAX_RETRY_COUNT', cast=int, default=5)
# default date where to end fetching sushi data
SUSHI_ATTEMPT_LAST_DATE = config('SUSHI_ATTEMPT_LAST_DATE', default='2017-01')
# this is the currency used for price calculation
REFERENCE_CURRENCY = config('REFERENCE_CURRENCY', default='CZK')

# Celus features configuration
# is this installation intended for one consortium
CONSORTIAL_INSTALLATION = config('CONSORTIAL_INSTALLATION', cast=bool, default=True)
ALLOW_MANUAL_UPLOAD = config('ALLOW_MANUAL_UPLOAD', cast=bool, default=True)
ALLOW_NONCOUNTER_DATA = config('ALLOW_NONCOUNTER_DATA', cast=bool, default=True)

# user authentication and registration
# should users be allowed to create accounts themselves
ALLOW_USER_REGISTRATION = config('ALLOW_USER_REGISTRATION', cast=bool, default=False)

# Allow user to create platforms
ALLOW_USER_CREATED_PLATFORMS = config('ALLOW_USER_CREATED_PLATFORMS', cast=bool, default=False)

# Allows to create new metrics during data import
# When False, user has to create metrics via admin,
# which will cause that import fails
AUTOMATICALLY_CREATE_METRICS = config('AUTOMATICALLY_CREATE_METRICS', cast=bool, default=True)

# Credentials which should be skipped during celery import
FAKE_SUSHI_URLS = ['https://sashimi.celus.net/']

# Should tags be visible in the UI - the following is passed to the frontend and used there
ENABLE_TAGS = config('ENABLE_TAGS', cast=bool, default=False)

# Should data coverage be visible in the UI
# the following is passed to the frontend and used there
ENABLE_DATA_COVERAGE = config('ENABLE_DATA_COVERAGE', cast=bool, default=False)
# the following influences the backend - empty data will be returned for the RTs listed below
# as of now, the computation of coverage for interest is not perfect, so we disable it by default
REPORT_TYPES_WITHOUT_COVERAGE = config(
    'REPORT_TYPES_WITHOUT_COVERAGE', cast=Csv(), default='interest'
)

# social authentication providers
SOCIAL_ACCOUNTS_SUPPORTED = config('SOCIAL_ACCOUNTS_SUPPORTED', cast=Csv(), default='')
SITE_ID = config('SITE_ID', cast=int, default=1)

# Celus servers from which the data will be harvested.
# These IPs are displayed in frontend so that customer knows,
# which addresses to register with his provider
HARVESTER_IPV4_ADDRESSES = config('HARVESTER_IPV4_ADDRESSES', cast=Csv(), default='')
HARVESTER_IPV6_ADDRESSES = config('HARVESTER_IPV6_ADDRESSES', cast=Csv(), default='')

# Some internal Celus config values
# The number of records that should be processed at once in import_counter_records
# it influences RAM consumption and speed.
# A reasonable minimum is 10_000 which has almost no RAM impact, but the speed is not that great.
# The default of 50_000 leads to about 2.5x speed up over 10k for a 500k file, but requires about
# extra 150 MB of RAM (for a 400 MB total).
# If there is enough memory available, it may help to increase the size to 100k or more
# but as there are not so many so large files there anyway, it probably does not make much sense
COUNTER_RECORD_BUFFER_SIZE = config('COUNTER_RECORD_BUFFER_SIZE', cast=int, default='50_000')

# Email
ADMINS = config('ADMINS', cast=Csv(cast=Csv(post_process=tuple), delimiter=';'), default='')
EMAIL_SUBJECT_PREFIX = config('EMAIL_SUBJECT_PREFIX', default='[Stats] ')
SERVER_EMAIL = config('SERVER_EMAIL', default='root@localhost')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='root@localhost')
EMAIL_HOST = config('EMAIL_HOST', default='localhost')

# password reset and invitation token timeout (in seconds)
# the purpose of the timeout is to guard against someone getting access to an old email account
# with unused reset tokens, so it should be safe to have it set to longer period than the default
# 3 days. It would make the invitation links much more convenient.
#
# https://docs.djangoproject.com/en/3.2/ref/settings/#password-reset-timeout
#
PASSWORD_RESET_TIMEOUT = config('PASSWORD_RESET_TIMEOUT', cast=int, default=864000)  # 10 days

CELUS_ADMIN_SITE_PATH = config('CELUS_ADMIN_SITE_PATH', default='wsEc67YNV2sq/')

EXPORTED_SETTINGS = [
    'ALLOW_EDUID_LOGIN',
    'ALLOW_EMAIL_LOGIN',
    'ALLOW_MANUAL_UPLOAD',
    'ALLOW_USER_CREATED_PLATFORMS',
    'ALLOW_USER_REGISTRATION',
    'AUTOMATICALLY_CREATE_METRICS',
    'CELUS_ADMIN_SITE_PATH',
    'CONSORTIAL_INSTALLATION',
    'ENABLE_TAGS',
    'ENABLE_DATA_COVERAGE',
    'HARVESTER_IPV4_ADDRESSES',
    'HARVESTER_IPV6_ADDRESSES',
    'LANGUAGES',
    'REFERENCE_CURRENCY',
    'SOCIAL_ACCOUNTS_SUPPORTED',
    'USES_ERMS',
    'EXPORT_DELETING_PERIOD',
    'ENABLE_RAW_DATA_IMPORT',
]

# Enables Automatic harvesting
AUTOMATIC_HARVESTING_ENABLED = config('AUTOMATIC_HARVESTING_ENABLED', cast=bool, default=True)

# Need to disable prometheus migrations when collecting static without DB
# see https://github.com/korfuri/django-prometheus/issues/34
PROMETHEUS_EXPORT_MIGRATIONS = config('PROMETHEUS_EXPORT_MIGRATIONS', cast=bool, default=True)

# sentry
SENTRY_ENVIRONMENT = config('SENTRY_ENVIRONMENT', default='unknown')
SENTRY_RELEASE = config('SENTRY_RELEASE', default='')
SENTRY_URL = config('SENTRY_URL', default='')
if SENTRY_URL:
    sentry_sdk.init(
        dsn=SENTRY_URL,
        integrations=[DjangoIntegration(), CeleryIntegration(), RedisIntegration()],
        send_default_pii=True,
        environment=SENTRY_ENVIRONMENT,
        release=f"celus-{SENTRY_RELEASE}" if SENTRY_RELEASE else None,
        traces_sample_rate=config('SENTRY_TRACE_SAMPLE_RATE', cast=float, default=1.0),
    )
    # ignore pycounter errors
    ignore_logger("pycounter.sushi")

# Releases and Changelog
RELEASES_SOURCEFILE = config('RELEASES_SOURCEFILE', default='RELEASES.yaml')

# nibbler
ENABLE_RAW_DATA_IMPORT = config(
    'ENABLE_RAW_DATA_IMPORT', cast=Choices(['All', 'PerOrg', 'None']), default='None'
)
ENABLE_NIBBLER_FOR_CELUS_FORMAT = config(
    'ENABLE_NIBBLER_FOR_CELUS_FORMAT', cast=bool, default=False
)
ENABLE_NIBBLER_FOR_COUNTER_FORMAT = config(
    'ENABLE_NIBBLER_FOR_COUNTER_FORMAT', cast=bool, default=False
)
