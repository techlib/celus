import logging

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


def ensure_accesslog_zero_fill_view():
    """Ensure the AccessLogCube zero-fill materialized view exists.

    - Skips if ClickHouse sync is disabled in settings.
    - Checks for existence of the materialized view first and logs an
      appropriate message.
    - Creates the view if missing.

    Can be called both from Django app startup (AppConfig.ready) and from
    test fixtures after ClickHouse storage is initialized.
    """
    if not getattr(settings, "CLICKHOUSE_SYNC_ACTIVE", False):
        logger.info("ClickHouse sync disabled; skipping materialized view setup")
        return

    from logs.cubes import AccessLogCube, create_ch_backend

    backend = create_ch_backend()
    table_name = backend.cube_to_table_name(AccessLogCube)
    view_name = "AccessLogCubeZeroFillView"

    create_query = f"""
    CREATE MATERIALIZED VIEW IF NOT EXISTS {view_name}
    REFRESH EVERY 30 MINUTE
    ENGINE = ReplacingMergeTree
    ORDER BY (date, platform_id, organization_id, report_type_id, metric_id)
    SETTINGS allow_nullable_key = 1
    POPULATE AS
    WITH
        -- derive full month range from data
        (SELECT toStartOfMonth(min(date)) FROM {table_name}) AS first_month,
        (SELECT toStartOfMonth(max(date)) FROM {table_name}) AS last_month_start,
        dateDiff('month', first_month, last_month_start) + 1 AS months_count,

        -- generate month starts across full range (oldest -> newest)
        months_data AS (
            SELECT arrayJoin(
                arrayMap(i -> addMonths(first_month, i), range(months_count))
            ) AS date
        ),

        -- distinct platform, organization, report_type, metric combinations
        combo_table AS (
            SELECT DISTINCT
                platform_id,
                organization_id,
                report_type_id,
                metric_id
            FROM {table_name}
        ),

        -- pre-aggregate sums per month + (platform, organization, report_type, metric)
        agg_table AS (
            SELECT
                toStartOfMonth(date) AS date,
                platform_id,
                organization_id,
                report_type_id,
                metric_id,
                SUM(value) AS total_value
            FROM {table_name}
            GROUP BY date, platform_id, organization_id, report_type_id, metric_id
        ),

        -- all month x (platform, organization, report_type, metric) pairs
        months_combos AS (
            SELECT
                m.date,
                d.platform_id,
                d.organization_id,
                d.report_type_id,
                d.metric_id
            FROM months_data AS m
            CROSS JOIN combo_table AS d
        )

    -- final join: will produce NULL total_value when the pair has no data
    SELECT
        md.date,
        md.platform_id,
        md.organization_id,
        md.report_type_id,
        md.metric_id,
        if(
        isNull(a.total_value)
        AND dictHas(
            'import_batch_rev',
            tuple(
            toString(md.report_type_id), /* todo make the keys not strings*/
            toString(md.organization_id),
            toString(md.platform_id),
            toDate(md.date)
            )
        ) = 1,
        0,
        a.total_value
        ) AS value

    FROM months_combos AS md
    LEFT JOIN agg_table AS a
        ON a.date = md.date
    AND a.platform_id = md.platform_id
    AND a.organization_id = md.organization_id
    AND a.report_type_id = md.report_type_id
    AND a.metric_id = md.metric_id
    SETTINGS join_use_nulls = 1;
    """

    try:
        with backend.pool.get_client() as client:
            exists = bool(client.execute(f"EXISTS TABLE {view_name}")[0][0])
            if exists:
                logger.info("Materialized view already present")
                return

            client.execute(create_query)
            logger.info("Materialized view created")
    except Exception as e:
        logger.error(f"Could not create materialized view: {e}")


class ReportingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "reporting"

    def ready(self):
        super().ready()
        ensure_accesslog_zero_fill_view()
