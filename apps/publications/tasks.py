"""
Celery tasks
"""
import logging

import celery
from core.logic.error_reporting import email_if_fails
from core.models import TaskProgress
from django.db.transaction import atomic
from organizations.models import Organization
from publications.logic.cleanup import clean_obsolete_platform_title_links, delete_platform_data
from publications.logic.sync import erms_sync_platforms
from publications.logic.title_management import find_mergeable_titles, merge_titles
from publications.models import Platform, TitleOverlapBatchState

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


@celery.shared_task
@email_if_fails
def delete_platform_data_task(
    platform_id: int, organization_ids: [int], delete_platform: bool = False
):
    tp = TaskProgress(task_id=celery.current_task.request.id)
    platform = Platform.objects.get(pk=platform_id)
    organizations = Organization.objects.filter(pk__in=organization_ids)
    delete_platform_data(
        platform, organizations, delete_platform, progress_monitor=tp.store_progress
    )


@celery.shared_task
@email_if_fails
@atomic
def process_title_overlap_batch_task(batch_id: int, domain_name: str = '/'):
    from publications.models import TitleOverlapBatch

    batch = TitleOverlapBatch.objects.filter(pk=batch_id).select_for_update().get()
    tp = TaskProgress(task_id=celery.current_task.request.id)
    if batch.state == TitleOverlapBatchState.PROCESSING:
        batch.process(
            progress_monitor=tp.store_progress,
            title_id_formatter=(lambda title_id: f'{domain_name}titles/{title_id}'),
        )
    else:
        logger.warning('Batch %d is not in processing state (%s)', batch_id, batch.state)
