import logging

import celery

from core.logic.error_reporting import email_if_fails
from .models import DataSource
from .task_support import cache_based_lock
from .logic.sync import sync_identities_with_erms, sync_users_with_erms

logger = logging.getLogger(__name__)


@celery.shared_task
@email_if_fails
def erms_sync_users_and_identities_task():
    with cache_based_lock('erms_sync_users_and_identities_task'):
        data_source, _created = DataSource.objects.get_or_create(short_name='ERMS',
                                                                 type=DataSource.TYPE_API)
        stats = sync_users_with_erms(data_source)
        logger.info('User import stats: %s', stats)
        stats = sync_identities_with_erms(data_source)
        logger.info('Identity import stats: %s', stats)
