"""
Celery tasks reside here
"""
import logging
from collections import Counter
from datetime import timedelta
import traceback

import celery
from django.db import DatabaseError
from django.db.models import Q
from django.db.transaction import atomic
from django.utils.timezone import now

from core.models import User
from core.context_managers import needs_clickhouse_sync
from core.logic.error_reporting import email_if_fails
from core.task_support import cache_based_lock
from core.tasks import async_mail_admins
from logs.exceptions import DataStructureError
from logs.logic.custom_import import import_custom_data
from logs.logic.attempt_import import import_one_sushi_attempt, check_importable_attempt
from logs.logic.clickhouse import process_one_import_batch_sync_log
from logs.logic.export import CSVExport
from logs.logic.materialized_interest import (
    sync_interest_by_import_batches,
    recompute_interest_by_batch,
    smart_interest_sync,
)
from logs.logic.custom_import import custom_import_preflight_check
from logs.logic.materialized_reports import (
    sync_materialized_reports,
    update_report_approx_record_count,
)
from logs.models import ImportBatchSyncLog, ManualDataUpload, MduState
from sushi.models import SushiFetchAttempt, AttemptStatus

logger = logging.getLogger(__file__)


@celery.shared_task
@email_if_fails
def sync_interest_task():
    """
    Synchronizes computed interest for import batches that were not processed yet
    """
    with cache_based_lock('sync_interest_task', blocking_timeout=10):
        sync_interest_by_import_batches()


@celery.shared_task
@email_if_fails
@atomic
def import_new_sushi_attempts_task():
    """
    Go over new sushi attempts that contain data and import them
    """
    try:
        # select_for_update locks fetch attempts
        attempts = SushiFetchAttempt.objects.select_for_update(nowait=True).filter(
            status=AttemptStatus.IMPORTING
        )
        count = attempts.count()
        logger.info('Found %d unprocessed successful download attempts matching criteria', count)

        for i, attempt in enumerate(attempts):
            logger.info('----- Importing attempt #%d -----', i)
            try:
                import_one_sushi_attempt(attempt)
            except Exception as e:
                # we catch any kind of error to make sure that the loop does not die
                logger.error('Importing sushi attempt #%d crashed: %s', attempt.pk, e)
                attempt.mark_crashed(e)

            finally:
                # Close the file (celery might keep the file opened)
                # Note that data_file should not be None otherwise FetchAttempt
                # wouldn't be in IMPORTING state
                attempt.data_file.close()

    except DatabaseError:
        logger.warning("Sushi import attempts are currently being processed.")


@celery.shared_task
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
            attempt.unprocess()

    except SushiFetchAttempt.DoesNotExist:
        # sushi attempt was deleted in the meantime
        # e.g. someone could remove credentials
        logger.warning("Sushi attempt '%s' was not found.", attempt_id)
        return
    except DatabaseError:
        logger.warning("Sushi attempt '%s' is being processed somewhere else.", attempt_id)
        return
    try:
        check_importable_attempt(attempt)
    except ValueError as e:
        logger.warning("Sushi attempt '%d' can't be imported: %s", attempt_id, str(e))
        if attempt.data_file:
            attempt.data_file.close()
        return
    try:
        import_one_sushi_attempt(attempt)
    except Exception as e:
        # we catch any kind of error to make sure that there is no crash
        logger.error('Importing sushi attempt #%d crashed: %s', attempt.pk, e)
        attempt.mark_crashed(e)
    finally:
        attempt.data_file.close()


@celery.shared_task
@email_if_fails
def recompute_interest_by_batch_task(queryset=None):
    """
    Run recompute_interest_by_batch to reconstruct interest for all batches.
    Useful when interest definitions change.
    """
    recompute_interest_by_batch(queryset=queryset)


@celery.shared_task
@email_if_fails
def smart_interest_sync_task():
    """
    Starts the `smart_interest_sync` function to synchronize all import batches that are
    not processed or out of sync
    """
    smart_interest_sync()


@celery.shared_task
@email_if_fails
def export_raw_data_task(query_params, filename_base, zip_compress=False):
    """
    Exports raw data into a file in the MEDIA directory
    """
    exporter = CSVExport(query_params, zip_compress=zip_compress, filename_base=filename_base)
    try:
        exporter.export_raw_accesslogs_to_file()
    except Exception as e:
        exporter.store_error()
        raise e


@celery.shared_task
@email_if_fails
def sync_materialized_reports_task():
    """
    Synchronizes materialized reports for import batches that were not processed yet
    """
    with cache_based_lock('sync_materialized_reports_task', blocking_timeout=10):
        sync_materialized_reports()


@celery.shared_task
@email_if_fails
def update_report_approx_record_count_task():
    """
    Synchronizes the `approx_record_count` values for all report types
    """
    with cache_based_lock('update_report_approx_record_count_task', blocking_timeout=10):
        update_report_approx_record_count()


@celery.shared_task
@email_if_fails
@needs_clickhouse_sync
@atomic
def process_outstanding_import_batch_sync_logs_task(age_threshold: int = 600):
    qs = (
        ImportBatchSyncLog.objects.exclude(state=ImportBatchSyncLog.STATE_NO_CHANGE)
        .filter(created__lt=now() - timedelta(seconds=age_threshold))
        .order_by('created')
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
@email_if_fails
def process_one_import_batch_sync_log_task(import_batch_id):
    process_one_import_batch_sync_log(import_batch_id)


@celery.shared_task
@email_if_fails
@atomic
def prepare_preflight(mdu_id: int):
    try:
        # select_for_update lock only a single fetch attempts
        mdu = ManualDataUpload.objects.select_for_update(nowait=True).get(pk=mdu_id)
        if mdu.state == MduState.PREFLIGHT:
            # preflight data already generated => skipping
            logger.warning(
                f"Preflight data (for mdu={mdu.pk}) are already generated: {mdu.preflight}"
            )
        elif mdu.state == MduState.INITIAL:
            mdu.preflight = custom_import_preflight_check(mdu)
            mdu.error = None
            mdu.error_details = None
            mdu.state = MduState.PREFLIGHT
            mdu.save()
        else:
            logger.error(f"Can't generate preflight data for mdu={mdu.pk} (state={mdu.state})")

    except ManualDataUpload.DoesNotExist:
        # mdu was deleted in the meantime
        logger.warning("mdu '%s' was not found.", mdu_id)

    except DatabaseError as e:
        logger.warning("mdu '%s' is already being processed. (%s)", mdu_id, e)
    except UnicodeDecodeError as e:
        mdu.log = str(e)
        mdu.error = "unicode-decode"
        mdu.error_details = {
            "exception": str(e),
            "traceback": traceback.format_exc(),
        }
        mdu.when_processed = now()
        mdu.state = MduState.PREFAILED
        mdu.save()

    except Exception as e:
        body = f"""\
{mdu.mail_report_format()}


Exception: {e}

Traceback: {traceback.format_exc()}
"""
        mdu.log = body
        mdu.error = "general"
        mdu.error_details = {
            "exception": str(e),
            "traceback": traceback.format_exc(),
        }
        mdu.when_processed = now()
        mdu.state = MduState.PREFAILED
        mdu.save()
        async_mail_admins.delay('MDU preflight check error', body)


@celery.shared_task
@email_if_fails
@atomic
def prepare_preflights():
    """ This should unstuck MDUs without preflight """
    for mdu in ManualDataUpload.objects.select_for_update(skip_locked=True).filter(
        Q(state=MduState.INITIAL)
        & Q(created__lt=now() - timedelta(minutes=5))  # don't start right away
    ):
        mdu.plan_preflight()


@celery.shared_task
@email_if_fails
@atomic
def import_manual_upload_data(mdu_id: int, user_id: int):
    try:
        mdu = ManualDataUpload.objects.select_for_update(nowait=True).get(
            pk=mdu_id, state=MduState.IMPORTING
        )
        user = User.objects.get(pk=user_id)
        res = import_custom_data(mdu, user)
        logger.info("Manual upload processed: %s", res)

    except ManualDataUpload.DoesNotExist:
        # probably mdu was deleted in the meantime
        logger.warning("mdu '%s' was not found.", mdu_id)

    except User.DoesNotExist:
        # user was deleted in the meantime
        # this should almost never happen
        logger.warning("user '%s' was not found.", user_id)

    except DatabaseError as e:
        logger.warning("mdu '%s' is already being processed. (%s)", mdu_id, e)

    except (Exception, DataStructureError) as e:
        # generic import error handling

        mdu.log = f"""\
{mdu.mail_report_format()}


Exception: {e}

Traceback: {traceback.format_exc()}
"""

        mdu.error = "clashing-data" if isinstance(e, DatabaseError) else "import-error"
        mdu.error_details = {
            "exception": str(e),
            "traceback": traceback.format_exc(),
        }
        mdu.when_processed = now()
        mdu.state = MduState.FAILED
        mdu.save()


@celery.shared_task
@email_if_fails
@atomic
def unstuck_import_manual_upload_data():
    """ This should unstuck unprocessed MDUs """
    for mdu in ManualDataUpload.objects.select_for_update(skip_locked=True).filter(
        Q(state=MduState.IMPORTING)
        & Q(created__lt=now() - timedelta(minutes=5))  # don't start right away
    ):
        import_manual_upload_data.delay(mdu.pk, mdu.user.pk)


@celery.shared_task
@email_if_fails
def reprocess_mdu_task(mdu_id):
    try:
        mdu = ManualDataUpload.objects.get(pk=mdu_id)
    except ManualDataUpload.DoesNotExist:
        logger.error(f'MDU #{mdu_id} for reprocessing does not exist')
    else:
        mdu.unprocess()
        import_manual_upload_data.delay(mdu.pk, mdu.user.pk)
