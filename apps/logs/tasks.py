"""
Celery tasks reside here
"""

import logging
import traceback
from collections import Counter
from datetime import timedelta
from random import randint
from time import monotonic
from typing import Optional

import celery
from core.context_managers import logged_task, needs_clickhouse_sync
from core.logic.error_reporting import email_if_fails
from core.models import User
from core.task_support import cache_based_lock
from core.tasks import async_mail_admins
from django.conf import settings
from django.db import DatabaseError
from django.db.models import Q
from django.db.transaction import atomic
from django.utils.timezone import now
from sushi.models import AttemptStatus, SushiFetchAttempt

from logs.exceptions import (
    DataAlreadyPresent,
    ImportNotPossible,
    MultipleReportTypes,
    NibblerErrors,
    OrganizationHasToBeSelected,
    UnknownReportTypeInPreflight,
)
from logs.logic.attempt_import import import_one_sushi_attempt
from logs.logic.cleanup import (
    find_organizationplatform_differences,
    find_split_accesslogs_with_the_same_title,
    fix_organizationplatform_differences,
)
from logs.logic.clickhouse import (
    compare_db_with_clickhouse,
    compare_titles_with_clickhouse,
    deal_with_comparison_results,
    process_one_import_batch_sync_log,
)
from logs.logic.custom_import import custom_import_preflight_check, import_custom_data
from logs.logic.export import CSVExport
from logs.logic.interest.computation import recompute_interest_by_batch, smart_interest_sync
from logs.logic.materialized_reports import (
    sync_materialized_reports,
    update_report_approx_record_count,
)
from logs.models import (
    FlexibleReportUserEmail,
    ImportBatch,
    ImportBatchSyncLog,
    ManualDataUpload,
    MduMethod,
    MduState,
)
from logs.serializers import FlexibleReportUserEmailNewSerializer

logger = logging.getLogger(__file__)


# how many attempts to import at once, should not be too much to avoid celery killing the task
# but not too little to avoid the celery scheduling overhead
IMPORT_BATCH_SIZE = 100


@celery.shared_task
@logged_task
@email_if_fails
def import_new_sushi_attempts_task():
    """
    Go over new sushi attempts that contain data and import them.
    We want to make sure that this task does not run forever, because it would be
    killed by Celery. So we limit the number of attempts to import to IMPORT_BATCH_SIZE and
    reschedule the task after that.
    """
    attempts = SushiFetchAttempt.objects.filter(status=AttemptStatus.IMPORTING).order_by("pk")
    count = attempts.count()
    # get the first 100 attempts to import and then try them one by one locking them one by one
    to_do = attempts.values_list("pk", flat=True)[:IMPORT_BATCH_SIZE]
    logger.info("Found %d unprocessed successful attempts, importing %d of them", count, len(to_do))

    for attempt_pk in to_do:
        with atomic():
            if attempt := attempts.select_for_update(skip_locked=True).get(pk=attempt_pk):
                logger.info("----- Importing attempt #%d -----", attempt.pk)
                try:
                    attempt.check_importable()
                    import_one_sushi_attempt(attempt)
                except Exception as e:
                    # we catch any kind of error to make sure that the loop does not die
                    logger.error("Importing sushi attempt #%d crashed: %s", attempt.pk, e)
                    attempt.mark_crashed(e)

                finally:
                    # Close the file (celery might keep the file opened)
                    if attempt.data_file:
                        attempt.data_file.close()
            else:
                logger.warning(
                    "----- Attempt #%d is no longer available for import -----", attempt_pk
                )
    if attempts.exists():
        # reschedule the task to import the next batch of attempts immediately
        import_new_sushi_attempts_task.delay()


@celery.shared_task
@logged_task
@email_if_fails
@atomic
def import_one_sushi_attempt_task(attempt_id: int, reimport: bool = False):
    """
    Tries to import a single sushi attempt task

    :attempt_id: pk of attempt to import
    :reimport: removes data and marks attempt as unprocessed before import
    """
    try:
        # select_for_update lock only a single fetch attempts
        attempt = SushiFetchAttempt.objects.select_for_update(nowait=True).get(pk=attempt_id)
        if reimport:
            attempt.reimport()

    except SushiFetchAttempt.DoesNotExist:
        # sushi attempt was deleted in the meantime
        # e.g. someone could remove credentials
        logger.warning("Sushi attempt '%s' was not found.", attempt_id)
        return
    except DatabaseError:
        logger.warning("Sushi attempt '%s' is being processed somewhere else.", attempt_id)
        return
    try:
        attempt.check_importable()
    except ValueError as e:
        logger.warning("Sushi attempt '%d' can't be imported: %s", attempt_id, str(e))
        if attempt.data_file:
            attempt.data_file.close()
        return
    try:
        import_one_sushi_attempt(attempt)
    except Exception as e:
        # we catch any kind of error to make sure that there is no crash
        logger.error("Importing sushi attempt #%d crashed: %s", attempt.pk, e)
        attempt.mark_crashed(e)
    finally:
        if attempt.data_file:
            attempt.data_file.close()
    # check the harvest status and create an Event when harvest is finished
    # (only if there is a connected fetch intention - in some tests it may not be so)
    if attempt.status == AttemptStatus.SUCCESS and hasattr(attempt, "fetchintention"):
        attempt.fetchintention.harvest.create_event_if_finished()


@celery.shared_task
@logged_task
@email_if_fails
def smart_interest_sync_task():
    """
    Starts the `smart_interest_sync` function to synchronize all import batches that are
    not processed or out of sync
    """
    smart_interest_sync()


@celery.shared_task
@logged_task
@email_if_fails
def sync_interest_for_superseded_import_batches_task():
    """
    Synchronizes interest for superseded import batches where the superseding batch was
    deleted (ending up with interest_ib being null due to on_delete=SET_NULL).
    """
    recompute_interest_by_batch(ImportBatch.objects.filter(interest_ib__isnull=True))


@celery.shared_task
@logged_task
@email_if_fails
def export_raw_data_task(query_params, filename_base, zip_compress=False):
    """
    Exports raw data into a file in the MEDIA directory
    """
    exporter = CSVExport(
        query_params,
        zip_compress=zip_compress,
        filename_base=filename_base,
        use_clickhouse=settings.CLICKHOUSE_QUERY_ACTIVE,
    )
    try:
        exporter.export_raw_accesslogs_to_file()
    except Exception as e:
        exporter.store_error()
        raise e


@celery.shared_task
@logged_task
@email_if_fails
def sync_materialized_reports_task():
    """
    Synchronizes materialized reports for import batches that were not processed yet
    """
    with cache_based_lock("sync_materialized_reports_task", blocking_timeout=10):
        sync_materialized_reports()


@celery.shared_task
@logged_task
@email_if_fails
def update_report_approx_record_count_task():
    """
    Synchronizes the `approx_record_count` values for all report types
    """
    with cache_based_lock("update_report_approx_record_count_task", blocking_timeout=10):
        update_report_approx_record_count()


@celery.shared_task
@logged_task
@email_if_fails
@needs_clickhouse_sync
@atomic
def process_outstanding_import_batch_sync_logs_task(age_threshold: int = 600):
    qs = (
        ImportBatchSyncLog.objects.exclude(state=ImportBatchSyncLog.STATE_NO_CHANGE)
        .filter(created__lt=now() - timedelta(seconds=age_threshold))
        .order_by("created")
        .select_for_update(skip_locked=True)
    )
    count = qs.count()
    if count:
        stats = Counter()
        for sync_log in qs:
            stats[sync_log.get_state_display()] += 1
        async_mail_admins.delay(
            "Unsynced import batches found",
            f"We found **{count}** import batches that were not immediatelly synced with "
            f"Clickhouse and remained unsynced. Their state is as follows: \n\n{stats}",
        )
    for sync_log in qs:
        process_one_import_batch_sync_log_task.delay(sync_log.pk)


@celery.shared_task
@logged_task
@email_if_fails
@atomic
def compare_db_with_clickhouse_task():
    """
    Compares the database with Clickhouse and sends an email with the results
    """
    start = monotonic()
    for fn in (compare_db_with_clickhouse, compare_titles_with_clickhouse):
        result = fn()
        if not result.is_ok():
            # there are some differences - we need to fix it and report it to admins
            deal_with_comparison_results(result)
            log = "\n".join(result.log)
            body = (
                f"The following difference were fixed between clickhouse and db:\n\n"
                f"**Differences found**:\n\n{log}\n\n**Stats**:\n\n{result.stats}\n\n"
                f"Duration: {monotonic() - start:.2f} s"
            )
            async_mail_admins.delay(
                f"Fixed differences between database and Clickhouse ({fn.__name__})", body
            )
            logger.warning("Send email about differences between database and Clickhouse: %s", body)


@celery.shared_task
@logged_task
@email_if_fails
def compare_db_with_clickhouse_delayed_task():
    """
    Schedules `compare_db_with_clickhouse_task` to be run in the future with a random delay.
    This is used to avoid running the task at the same time on all containers.
    """
    delay = randint(0, 30 * 60)
    logger.info("Scheduling `compare_db_with_clickhouse_task` in %d seconds", delay)
    compare_db_with_clickhouse_task.apply_async(countdown=delay)


@celery.shared_task
@logged_task
@email_if_fails
def process_one_import_batch_sync_log_task(import_batch_id):
    process_one_import_batch_sync_log(import_batch_id)


@celery.shared_task
@logged_task
@email_if_fails
@atomic
def prepare_preflight(mdu_id: int):
    try:
        # select_for_update lock only a single fetch attempts
        mdu = ManualDataUpload.objects.select_for_update(nowait=True).get(pk=mdu_id)
        mdu.check_self_checksum()  # validate checksum of the underlying file
        if mdu.state == MduState.PREFLIGHT:
            # preflight data already generated => skipping
            logger.warning(
                f"Preflight data (for mdu={mdu.pk}) are already generated: {mdu.preflight}"
            )
            return

        elif mdu.state == MduState.CONFIRMED:
            if mdu.method == MduMethod.RAW:
                from nibbler.logic.processing import get_errors, is_success  # noqa - slow import
                from nibbler.models import get_report_types_from_nibbler_output  # noqa - slow import

                # update method if it was updated
                nibbler_output, mdu.method = mdu.get_nibbler_output()

                # detect report type from existing data
                if not is_success(nibbler_output):
                    raise NibblerErrors(get_errors(nibbler_output))

                report_types, rt_names = get_report_types_from_nibbler_output(nibbler_output)
                rt_names = ", ".join(f'"{e}"' for e in set(rt_names))

                if not report_types:
                    # No report types found
                    raise UnknownReportTypeInPreflight(
                        f"File parsed, but no matching ReportType found: {rt_names}"
                    )

                if len(report_types) > 1:
                    # Altough nibbler allows you to have different report_types on
                    # different sheets, in celus you may have only the same report type
                    # on all sheets
                    raise MultipleReportTypes(report_types)

                mdu.report_type = report_types[0]

            mdu.preflight = custom_import_preflight_check(mdu)
            mdu.error = None
            mdu.error_details = None
            mdu.state = MduState.PREFLIGHT
            mdu.save()
        else:
            logger.error(f"Can't generate preflight data for mdu={mdu.pk} (state={mdu.state})")
            return

    except ManualDataUpload.DoesNotExist:
        # mdu was deleted in the meantime
        logger.warning("mdu '%s' was not found.", mdu_id)
        return

    except DatabaseError as e:
        logger.warning("mdu '%s' is already being processed. (%s)", mdu_id, e)
        return

    except UnicodeDecodeError as e:
        encoded = str(e).encode("unicode_escape")
        mdu.log = encoded
        mdu.error = "unicode-decode"
        mdu.error_details = {
            "exception": encoded.decode(),
            "traceback": traceback.format_exc().encode("unicode_escape").decode(),
        }
        mdu.when_processed = now()
        mdu.state = MduState.PREFAILED
        mdu.save()

    except NibblerErrors as e:
        mdu.log = "\n\n".join(repr(i) for i in e.errors)
        mdu.error = "nibbler"
        mdu.error_details = {
            "exception": str(e).encode("unicode_escape").decode(),
            "traceback": traceback.format_exc(),
            "nibbler": [i.dict() for i in e.errors],
        }
        mdu.when_processed = now()
        mdu.state = MduState.PREFAILED
        mdu.save()

    except OrganizationHasToBeSelected as e:
        mdu.log = str(e)
        mdu.error = "no-organization-selected"
        mdu.error_details = {"exception": str(e), "traceback": traceback.format_exc()}
        mdu.when_processed = now()
        mdu.state = MduState.PREFAILED
        mdu.save()

    except Exception as e:
        body = f"""\
{mdu.mail_report_format()}


Exception: {e}

Traceback: {traceback.format_exc()}
"""
        error = "general"
        if isinstance(e, UnknownReportTypeInPreflight):
            error = "unknown-report-type"
        elif isinstance(e, MultipleReportTypes):
            error = "multiple-report-type"

        mdu.log = body.encode("unicode_escape")
        mdu.error = error
        mdu.error_details = {
            "exception": str(e).encode("unicode_escape").decode(),
            "traceback": traceback.format_exc().encode("unicode_escape").decode(),
        }
        mdu.when_processed = now()
        mdu.state = MduState.PREFAILED
        mdu.save()
        async_mail_admins.delay("MDU preflight check error", body)

    # Try to close the file (celery might keep the file opened)
    try:
        mdu.data_file.close()
    except Exception:
        pass


@celery.shared_task
@logged_task
@email_if_fails
@atomic
def prepare_preflights():
    """This should unstuck MDUs without preflight"""
    for mdu in ManualDataUpload.objects.select_for_update(skip_locked=True).filter(
        Q(state=MduState.CONFIRMED)
        & Q(created__lt=now() - timedelta(minutes=5))  # don't start right away
    ):
        mdu.plan_preflight()


@celery.shared_task
@logged_task
@email_if_fails
@atomic
def import_manual_upload_data(mdu_id: int, user_id: Optional[int] = None):
    try:
        mdu = ManualDataUpload.objects.select_for_update(nowait=True).get(
            pk=mdu_id, state=MduState.IMPORTING
        )
        mdu.check_self_checksum()  # check file integrity using a stored checksum
        user = User.objects.get(pk=user_id) if user_id else mdu.user
        if mdu.preflight["log_count"] == 0:
            # Try to fill in empty import batches based on provided months
            res = import_custom_data(mdu, user, empty=True)
            logger.info("Filling in empty import batches: %s", res)
        else:
            res = import_custom_data(mdu, user)
            logger.info("Manual upload processed: %s", res)

    except ManualDataUpload.DoesNotExist:
        # probably mdu was deleted in the meantime
        logger.warning("mdu '%s' was not found.", mdu_id)
        return

    except User.DoesNotExist:
        # user was deleted in the meantime
        # this should almost never happen
        logger.warning("user '%s' was not found.", user_id)
        return

    except DatabaseError as e:
        logger.warning("mdu '%s' is already being processed. (%s)", mdu_id, e)
        return

    except NibblerErrors as e:
        mdu.log = "\n\n".join(repr(i) for i in e.errors)
        mdu.error = "nibbler"
        mdu.error_details = {
            "exception": str(e),
            "traceback": traceback.format_exc(),
            "nibbler": [i.dict() for i in e.errors],
        }
        mdu.when_processed = now()
        mdu.state = MduState.FAILED
        mdu.save()

    except (Exception, DataAlreadyPresent, ImportNotPossible) as e:
        # generic import error handling

        mdu.log = f"""\
{mdu.mail_report_format()}


Exception: {e}

Traceback: {traceback.format_exc()}
"""

        if isinstance(e, DataAlreadyPresent):
            mdu.error = "clashing-data"
        elif isinstance(e, ImportNotPossible):
            mdu.error = "import-not-possible"
        else:
            mdu.error = "import-error"
        mdu.error_details = {"exception": str(e), "traceback": traceback.format_exc()}
        mdu.when_processed = now()
        mdu.state = MduState.FAILED
        mdu.save()

    # Try to close the file (celery might keep the file opened)
    try:
        mdu.data_file.close()
    except Exception:
        pass


@celery.shared_task
@logged_task
@email_if_fails
@atomic
def unstuck_import_manual_upload_data():
    """This should unstuck unprocessed MDUs"""
    for mdu in ManualDataUpload.objects.select_for_update(skip_locked=True).filter(
        Q(state=MduState.IMPORTING)
        & Q(created__lt=now() - timedelta(minutes=5))  # don't start right away
    ):
        import_manual_upload_data.delay(mdu.pk, mdu.user_id)


@celery.shared_task
@logged_task
@email_if_fails
def reprocess_mdu_task(mdu_id):
    try:
        mdu = ManualDataUpload.objects.get(pk=mdu_id)
    except ManualDataUpload.DoesNotExist:
        logger.error(f"MDU #{mdu_id} for reprocessing does not exist")
    else:
        mdu.unprocess()
        import_manual_upload_data.delay(mdu.pk, mdu.user_id)


@celery.shared_task
@logged_task
@email_if_fails
@atomic
def sync_organizationplatform_records_task(reason: Optional[str] = None):
    missing, extra = find_organizationplatform_differences()
    if missing or extra:
        fix_organizationplatform_differences(missing, extra)
        reason_str = f"Reason: {reason}\n" if reason else ""
        async_mail_admins.delay(
            "OrganizationPlatform records were out of sync",
            reason_str
            + f"Missing: {len(missing)}\nExtra: {len(extra)}\n\nProblems have already been fixed.",
        )


@celery.shared_task
@logged_task
@email_if_fails
@atomic
def find_split_accesslogs_with_the_same_title_task():
    stats = find_split_accesslogs_with_the_same_title(fix_it=True)
    if stats:
        async_mail_admins.delay(
            "Found and fixed split accesslogs with the same title",
            f"Stats: {stats}\n\nNo manual intervention is needed.",
        )


@celery.shared_task
@logged_task
@email_if_fails
def send_report_mailing_raw_task(data: dict):
    """
    Send a report mailing using a dict of raw data as input.
    """
    logger.info("Sending report mailing: %s", data)
    serializer = FlexibleReportUserEmailNewSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    logger.info("Serializer is valid: %s", serializer.validated_data)
    # the serializer creates the instance and saves it to the database
    # therefore we create the instance manually here - we don't want to save it
    FlexibleReportUserEmail(**serializer.validated_data).send_email()


@celery.shared_task
@logged_task
@email_if_fails
def send_due_report_mailings_task():
    """
    Send due report mailings
    """
    for fru in FlexibleReportUserEmail.objects.all():
        # next_send is a property, so we need to evaluate it for each object
        if fru.next_send <= now().date():
            with atomic():
                if (
                    fru := FlexibleReportUserEmail.objects.select_for_update(skip_locked=True)
                    .filter(pk=fru.pk)
                    .first()
                ):
                    logger.info("Sending due report mailing: #%d; %s", fru.pk, fru)
                    fru.send_email()
                else:
                    logger.warning(
                        "FlexibleReportUserEmail #%d is being processed by another worker", fru.pk
                    )
