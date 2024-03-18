"""
Intended to store all code needed to create and possibly update the clickhouse database
used for storing accesslogs.
"""
import logging

from django.core.management.base import BaseCommand

from logs.cubes import AccessLogCube, create_ch_backend

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Converts the clickhouse table (originally CollapsingMergeTree) to a MergeTree table. "
        "It should ideally be run when there is no traffic to the website, or the uwsgi "
        "server and the celery workers are stopped. The reason is that the table will be "
        "temprorarily empty."
    )

    def handle(self, *args, **options):
        from django.conf import settings

        if settings.CLICKHOUSE_SYNC_ACTIVE:
            # we want a fresh connection to clickhouse
            backend = create_ch_backend()
            with backend.pool.get_client() as client:
                # first rename the table to something temporary so that it does not get modified
                logger.info("Renaming the original table")
                table_name = backend.cube_to_table_name(AccessLogCube)
                client.execute(f"RENAME TABLE {table_name} TO {table_name}_old")
                # create the new table according to the current definition - this way the time when
                # the table is not available is minimized (but it will be empty)
                logger.info("Creating the new table")
                backend.initialize_storage(AccessLogCube)
                backend.sync_storage(AccessLogCube)
                # then make sure the table is optimized = fully collapsed
                logger.info(
                    "Optimizing the old table so it is fully collapsed and can be directly copied"
                )
                client.execute(f"OPTIMIZE TABLE {table_name}_old FINAL")
                # then copy the data from the old table to the new one
                # the number of columns is different (we are dropping sign), so we must explicitly
                # specify the columns
                logger.info("Copying the data from the old table to the new one")
                client.execute(
                    f"""INSERT INTO {table_name}
                    (report_type_id, organization_id, platform_id, date, metric_id, target_id,
                     item_id, dim1, dim2, dim3, dim4, dim5, dim6, dim7, dim8, import_batch_id, id,
                     value)
                    SELECT report_type_id, organization_id, platform_id, date, metric_id, target_id,
                    item_id, dim1, dim2, dim3, dim4, dim5, dim6, dim7, dim8, import_batch_id, id,
                    value
                    FROM {table_name}_old"""
                )
                # then drop the old table
                logger.info("Dropping the old table")
                client.execute(f"DROP TABLE {table_name}_old")
        else:
            logger.warning("Clickhouse sync is disabled, nothing to do")
