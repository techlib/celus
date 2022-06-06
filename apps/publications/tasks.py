"""
Celery tasks
"""
import logging

import celery

from core.logic.error_reporting import email_if_fails
from publications.logic.cleanup import clean_obsolete_platform_title_links
from publications.logic.sync import erms_sync_platforms
from publications.logic.title_management import find_mergeable_titles, merge_titles

logger = logging.getLogger(__name__)


@celery.shared_task
@email_if_fails
def erms_sync_platforms_task():
    erms_sync_platforms()


@celery.shared_task
@email_if_fails
def clean_obsolete_platform_title_links_task():
    clean_obsolete_platform_title_links()


@celery.shared_task
@email_if_fails
def merge_titles_task():
    count = 0
    for titles in find_mergeable_titles():
        count += 1
        merge_titles(titles)
    logger.info('Merged %d sets of titles', count)
