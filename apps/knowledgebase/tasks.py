import celery
from django.db import transaction, DatabaseError

from core.logic.error_reporting import email_if_fails

from .models import PlatformImportAttempt, ImportAttempt, RouterSyncAttempt


@celery.shared_task
@email_if_fails
def update_platforms(attempt_id: int):
    attempt = PlatformImportAttempt.objects.get(pk=attempt_id)

    if attempt.kind != ImportAttempt.KIND_PLATFORM:
        raise ValueError(f"Wrong kind {attempt.kind} expected {ImportAttempt.KIND_PLATFORM}")

    attempt.perform()


@celery.shared_task
@email_if_fails
def sync_route(attempt_id: int):
    with transaction.atomic():
        try:
            attempt = RouterSyncAttempt.objects.select_for_update(nowait=True).get(pk=attempt_id)
            attempt.trigger()
        except DatabaseError:
            # Already being processed
            pass


@celery.shared_task
@email_if_fails
def sync_routes():
    for attempt in RouterSyncAttempt.objects.filter(done__isnull=True):
        attempt.plan()
