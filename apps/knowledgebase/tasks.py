import celery
from core.logic.error_reporting import email_if_fails
from core.models import DataSource
from django.db import DatabaseError, transaction

from .models import (
    ImportAttempt,
    ParserDefinitionImportAttempt,
    PlatformImportAttempt,
    ReportTypeImportAttempt,
    RouterSyncAttempt,
)


@celery.shared_task
@email_if_fails
def sync_platforms_with_knowledgebase_task():
    sources = list(DataSource.objects.filter(type=DataSource.TYPE_KNOWLEDGEBASE))
    for source in sources:
        attempt = PlatformImportAttempt.objects.create(
            kind=PlatformImportAttempt.KIND_PLATFORM, source=source
        )
        attempt.perform()


@celery.shared_task
@email_if_fails
def update_platforms(attempt_id: int):
    attempt = PlatformImportAttempt.objects.get(pk=attempt_id)

    if attempt.kind != ImportAttempt.KIND_PLATFORM:
        raise ValueError(f"Wrong kind {attempt.kind} expected {ImportAttempt.KIND_PLATFORM}")

    attempt.perform()


@celery.shared_task
@email_if_fails
def sync_report_types_with_knowledgebase_task():
    sources = list(DataSource.objects.filter(type=DataSource.TYPE_KNOWLEDGEBASE))
    for source in sources:
        attempt = ReportTypeImportAttempt.objects.create(
            kind=ReportTypeImportAttempt.KIND_REPORT_TYPE, source=source
        )
        attempt.perform()


@celery.shared_task
@email_if_fails
def update_report_types(attempt_id: int):
    attempt = ReportTypeImportAttempt.objects.get(pk=attempt_id)

    if attempt.kind != ImportAttempt.KIND_REPORT_TYPE:
        raise ValueError(f"Wrong kind {attempt.kind} expected {ImportAttempt.KIND_REPORT_TYPE}")

    attempt.perform()


@celery.shared_task
@email_if_fails
def update_parser_definitions(attempt_id: int):
    attempt = ParserDefinitionImportAttempt.objects.get(pk=attempt_id)

    if attempt.kind != ImportAttempt.KIND_PARSER_DEFINITION:
        raise ValueError(
            f"Wrong kind {attempt.kind} expected {ImportAttempt.KIND_PARSER_DEFINITION}"
        )

    attempt.perform()


@celery.shared_task
@email_if_fails
def sync_parser_definitions_with_knowledgebase_task():
    sources = list(DataSource.objects.filter(type=DataSource.TYPE_KNOWLEDGEBASE))
    for source in sources:
        attempt = ParserDefinitionImportAttempt.objects.create(
            kind=ParserDefinitionImportAttempt.KIND_PARSER_DEFINITION, source=source
        )
        attempt.perform()


@celery.shared_task
@email_if_fails
def sync_all_with_knowledgebase_task():
    with transaction.atomic():
        sync_platforms_with_knowledgebase_task()
        sync_report_types_with_knowledgebase_task()
        sync_parser_definitions_with_knowledgebase_task()


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
