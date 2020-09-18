import celery

from .models import PlatformImportAttempt, ImportAttempt

from core.logic.error_reporting import email_if_fails


@celery.shared_task
@email_if_fails
def update_platforms(attempt_id: int):
    attempt = PlatformImportAttempt.objects.get(pk=attempt_id)

    if attempt.kind != ImportAttempt.KIND_PLATFORM:
        raise ValueError(f"Wrong kind {attempt.kind} expected {ImportAttempt.KIND_PLATFORM}")

    attempt.perform()
