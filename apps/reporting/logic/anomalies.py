import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from logs.cubes import AccessLogCube, create_ch_backend
from logs.logic.clickhouse import ZERO_FILL_VIEW_NAME
from logs.models import ReportType

logger = logging.getLogger(__name__)


@dataclass
class AnomalySource:
    anomaly_id: int
    anomaly_date: str
    platform_id: int
    organization_id: int
    report_type_id: int
    metric_id: int

    def to_tuple(self) -> tuple[int, str, int, int, int, int]:
        return (
            self.anomaly_id,
            self.anomaly_date,
            self.platform_id,
            self.organization_id,
            self.report_type_id,
            self.metric_id,
        )


@dataclass
class HistoryItem:
    month: datetime
    value: float


class AnomalyDetector:
    def __init__(
        self, month_from: str, month_to: str, organization_ids: Sequence[int] | None = None
    ):
        self.month_from = month_from
        self.month_to = month_to
        self.organization_ids = list(organization_ids or [])
        self.backend = create_ch_backend()
        self.anomalies: list[AnomalySource] = []

    def _get_reasons_by_group(
        self, combos: list[AnomalySource], group_select: str, group_text_sql: str
    ) -> tuple[list[tuple], list[str]]:
        """
        Internal helper that runs the common ClickHouse query to fetch anomaly reasons
        grouped by an arbitrary key (dimension or target_id).

        Parameters:
            combos: list of AnomalySource
            group_select: SQL snippet for the 'agg' CTE that must SELECT the grouping key
                           aliased as "group_key" (e.g. "target_id AS group_key" or
                           "dim1 AS group_key")
            group_text_sql: SQL snippet producing human-readable label from dictionaries
                             using the alias agg.group_key (e.g.
                             "dictGet('title', 'name', toUInt64(agg.group_key))")
            order_by: ORDER BY expression for the final SELECT

        Returns:
            (rows, column_names)
        """

        table_name = self.backend.cube_to_table_name(AccessLogCube)

        query = f"""
        WITH
            tuples AS (
                SELECT arrayJoin(%(combos)s) AS t
            ),
            expanded AS (
                SELECT
                    t.1 AS anomaly_id,
                    toStartOfMonth(toDate(t.2)) AS anchor_month,
                    subtractYears(toStartOfMonth(toDate(t.2)), 1) AS one_year_ago,
                    subtractMonths(toStartOfMonth(toDate(t.2)), 1) AS last_month,
                    toUInt32(t.3) AS platform_id,
                    toUInt32(t.4) AS organization_id,
                    toUInt32(t.5) AS report_type_id,
                    toUInt32(t.6) AS metric_id
                FROM tuples
            ),
            bounds AS (
                SELECT
                    min(one_year_ago) AS min_since,
                    -- we need to include the anchor month in the base so that
                    -- agg has a row for the anchor_date to join on
                    max(anchor_month) AS max_until
                FROM expanded
            ),
            months AS (
                SELECT addMonths(assumeNotNull((SELECT min_since FROM bounds)), number) AS date
                FROM numbers(
                    toUInt64(
                        dateDiff(
                            'month',
                            assumeNotNull((SELECT min_since FROM bounds)),
                            assumeNotNull((SELECT max_until FROM bounds))
                        ) + 1
                    )
                )
            ),
            base AS (
                SELECT
                    a.date AS date,
                    {group_select},
                    a.platform_id AS platform_id,
                    a.organization_id AS organization_id,
                    a.report_type_id AS report_type_id,
                    a.metric_id AS metric_id,
                    SUM(a.value) AS total_value
                FROM {table_name} a
                WHERE
                    (a.platform_id, a.organization_id, a.report_type_id, a.metric_id)
                        IN %(combos_base)s
                    AND a.date > (SELECT min_since FROM bounds)
                    AND a.date <= (SELECT max_until FROM bounds)
                GROUP BY
                    a.date,
                    group_key,
                    a.platform_id,
                    a.organization_id,
                    a.report_type_id,
                    a.metric_id
            ),
            groups AS (
                SELECT DISTINCT
                    group_key,
                    platform_id,
                    organization_id,
                    report_type_id,
                    metric_id
                FROM base
            ),
            base_filled AS (
                SELECT
                    m.date AS date,
                    toRelativeMonthNum(toStartOfMonth(m.date)) AS month_num,
                    g.group_key AS group_key,
                    g.platform_id AS platform_id,
                    g.organization_id AS organization_id,
                    g.report_type_id AS report_type_id,
                    g.metric_id AS metric_id,
                    coalesce(b.total_value, 0) AS total_value
                FROM groups g
                CROSS JOIN months m
                LEFT JOIN base b ON b.date = m.date
                    AND b.group_key = g.group_key
                    AND b.platform_id = g.platform_id
                    AND b.organization_id = g.organization_id
                    AND b.report_type_id = g.report_type_id
                    AND b.metric_id = g.metric_id
            ),
            agg AS (
                SELECT
                    bf.date AS date,
                    bf.group_key AS group_key,
                    bf.platform_id AS platform_id,
                    bf.organization_id AS organization_id,
                    bf.report_type_id AS report_type_id,
                    bf.metric_id AS metric_id,
                    bf.total_value AS total_value,
                    bf.month_num AS month_num,
                    quantilesExact(0.25, 0.5, 0.75)(total_value) OVER (
                        PARTITION BY
                            group_key,
                            platform_id,
                            organization_id,
                            report_type_id,
                            metric_id
                        ORDER BY month_num
                        RANGE BETWEEN 12 PRECEDING AND 1 PRECEDING
                    ) AS q,
                    uniqExact(group_key) OVER (
                        PARTITION BY platform_id,
                        organization_id,
                        report_type_id,
                        metric_id
                        ORDER BY month_num
                        RANGE BETWEEN 12 PRECEDING AND CURRENT ROW
                    ) AS group_count
                FROM base_filled AS bf
            )
        SELECT
            e.anomaly_id,
            e.anchor_month,
            agg.date,
            agg.group_key,
            {group_text_sql} AS group_text,
            agg.total_value,
            agg.q[2] AS median,
            (agg.q[3] - agg.q[1]) AS iqr,
            (agg.q[1] - 5 * iqr) AS lower_bound,
            (agg.q[3] + 5 * iqr) AS upper_bound,
            agg.group_count AS group_count,
            (agg.total_value - agg.q[2]) AS median_diff,
            abs(agg.total_value - agg.q[2]) AS abs_median_diff,
            agg.platform_id,
            agg.organization_id,
            agg.report_type_id AS report_type_id,
            agg.metric_id
        FROM expanded e
        INNER JOIN agg
            ON agg.platform_id = e.platform_id
            AND agg.organization_id = e.organization_id
            AND agg.report_type_id = e.report_type_id
            AND agg.metric_id = e.metric_id
            AND agg.date = e.anchor_month
        WHERE
            (
                agg.total_value < lower_bound
                OR agg.total_value > upper_bound
            )
            AND abs_median_diff > 15
            AND notEmpty(group_text)
        ORDER BY agg.group_key
        """

        combos_tuples = [c.to_tuple() for c in combos]
        combos_base = list(
            {(c.platform_id, c.organization_id, c.report_type_id, c.metric_id) for c in combos}
        )
        with self.backend.pool.get_client() as client:
            start = time.monotonic()
            rows, columns = client.execute(
                query, {"combos": combos_tuples, "combos_base": combos_base}, with_column_types=True
            )
            logger.debug(
                f"Clickhouse anomaly reasons query took {time.monotonic() - start:.2f} seconds"
            )

        col_names = [name for name, _ in columns]
        return rows, col_names

    def _get_dimension_data(self) -> dict[int, list[dict]]:
        """
        For each dimension, try to find its value that explains the anomaly.
        Returns list of dims and their values that deviate significantly.

        Output mapping:
        (anomaly_id) -> [
            {"type": "dim$n", "target_id_text": str, "total_value": int, "median": int,
            "median_diff": int}
        ]
        """
        # Build report_type_id -> list of dimension short_names in order
        report_type_ids = {c.report_type_id for c in self.anomalies}
        rt_map = ReportType.objects.in_bulk(report_type_ids)
        rt_id_to_dim_names: dict[int, list[str]] = {}
        for rt_id, rt in rt_map.items():
            dims = getattr(rt, "dimensions_sorted", [])
            rt_id_to_dim_names[rt_id] = [dim.short_name for dim in dims]

        by_anomaly: dict[int, list[dict]] = defaultdict(list)

        for dim_index in range(1, 9):
            # Filter combos to those whose report type actually has this dimension position
            combos_for_dim = [
                c
                for c in self.anomalies
                if len(rt_id_to_dim_names.get(c.report_type_id, [])) >= dim_index
            ]
            if not combos_for_dim:
                continue
            dim_col = f"dim{dim_index}"
            rows, col_names = self._get_reasons_by_group(
                combos_for_dim,
                group_select=f"{dim_col} AS group_key",
                group_text_sql="dictGet('dim', 'text', toUInt64(agg.group_key))",
            )

            for row in rows:
                rec = dict(zip(col_names, row, strict=True))
                anomaly_id = rec.get("anomaly_id")
                # Pick correct dimension label for this report type and dim index
                dim_names = rt_id_to_dim_names.get(rec["report_type_id"], [])
                dim_label = dim_names[dim_index - 1] if len(dim_names) >= dim_index else dim_col
                item = {
                    "type": dim_label,
                    "target_id_text": rec.get("group_text"),
                    "total_value": rec.get("total_value"),
                    "median": rec.get("median"),
                    "median_diff": rec.get("median_diff"),
                    "group_count": rec.get("group_count"),
                    "dim": dim_col,
                }
                by_anomaly[anomaly_id].append(item)

        return by_anomaly

    def _get_title_data(self) -> dict[int, list[dict]]:
        """
        Try to find titles that explain the anomaly.
        Returns titles that deviate significantly.

        Output mapping:
        (anomaly_id) -> [
            {"type": "title", "target_id_text": str, "total_value": int, "median": int,
            "median_diff": int}
        ]
        """

        rows, col_names = self._get_reasons_by_group(
            self.anomalies,
            group_select="target_id AS group_key",
            group_text_sql="dictGet('title', 'name', toUInt64(agg.group_key))",
        )

        by_anomaly: dict[int, list[dict]] = defaultdict(list)
        for row in rows:
            rec = dict(zip(col_names, row, strict=True))
            anomaly_id = rec.get("anomaly_id")
            item = {
                "type": "title",
                "target_id_text": rec.get("group_text"),
                "total_value": rec.get("total_value"),
                "median": rec.get("median"),
                "median_diff": rec.get("median_diff"),
                "group_count": rec.get("group_count"),
                "dim": "target",
            }
            by_anomaly[anomaly_id].append(item)

        return by_anomaly

    def _get_historical_data(self) -> dict[int, list[HistoryItem]]:
        """
        Fetches 12 month history of values for a given list of AnomalySources.
        Returns mapping: anomaly_id -> list of {month: YYYY-MM-DD, total_value: int}
        """

        query = f"""
        WITH
            tuples AS (SELECT arrayJoin(%(combos)s) AS t),
            expanded AS (
                SELECT
                    t.1 AS anomaly_id,
                    toDate(t.2) AS anchor_month,
                    toStartOfMonth(toDate(t.2)) AS last_month_start,
                    addMonths(toStartOfMonth(toDate(t.2)), -12) AS first_month,
                    toUInt32(t.3) AS platform_id,
                    toUInt32(t.4) AS organization_id,
                    toUInt32(t.5) AS report_type_id,
                    toUInt32(t.6) AS metric_id
                FROM tuples
            )
        SELECT
            e.anomaly_id,
            a.date AS month,
            a.value AS value
        FROM expanded e
        JOIN {ZERO_FILL_VIEW_NAME} a
            ON a.platform_id = e.platform_id
        AND a.organization_id = e.organization_id
        AND a.report_type_id = e.report_type_id
        AND a.metric_id = e.metric_id
        AND a.date >= e.first_month
        AND a.date < addMonths(e.last_month_start, 1)
        ORDER BY
            a.date
        """
        # Convert dataclass combos to tuple format required by ClickHouse
        combos_tuples = [c.to_tuple() for c in self.anomalies]

        with self.backend.pool.get_client() as client:
            start = time.monotonic()
            rows, _ = client.execute(query, {"combos": combos_tuples}, with_column_types=True)
            logger.debug(
                f"Clickhouse historical data query took {time.monotonic() - start:.2f} seconds"
            )

        # Build mapping: anomaly_id -> list of HistoryItem

        history_data: dict[int, list[HistoryItem]] = {}
        for anomaly_id, month_val, value in rows:
            history_data.setdefault(anomaly_id, []).append(
                HistoryItem(month=month_val, value=value)
            )

        return history_data

    def get_anomalies(self) -> list[dict]:
        query = f"""
        WITH
            toStartOfMonth(toDate(%(cutoff_date)s)) AS first_cutoff,
            toStartOfMonth(toDate(%(cutoff_date_to)s)) AS last_cutoff,

            -- generate all cutoff months
            cutoffs AS (
                SELECT arrayJoin(
                        arrayMap(i -> addMonths(first_cutoff, i),
                                    range(dateDiff('month', first_cutoff, last_cutoff) + 1))
                    ) AS cutoff_date
            )

            -- 1) Quantiles per group per cutoff
            , quantiles_per_group AS (
                SELECT
                    c.cutoff_date,
                    v.platform_id,
                    v.organization_id,
                    v.report_type_id,
                    v.metric_id,
                    quantilesExact(0.25, 0.5, 0.75)(v.value) AS q,
                    count(v.value) AS num_values
                FROM cutoffs c
                JOIN {ZERO_FILL_VIEW_NAME} v
                ON v.date >= subtractYears(c.cutoff_date, 1)
                AND v.date < c.cutoff_date
                {"AND organization_id IN %(organization_ids)s" if self.organization_ids else ""}
                GROUP BY c.cutoff_date,
                            v.platform_id,
                            v.organization_id,
                            v.report_type_id,
                            v.metric_id
            )

            -- 2) Outlier detection for each cutoff
            SELECT
                c.cutoff_date as date,
                v.platform_id as platform_id,
                v.organization_id as organization_id,
                v.report_type_id as report_type_id,
                v.metric_id as metric_id,
                dictGet('platform', 'short_name', toUInt64(v.platform_id)) AS platform_short_name,
                dictGet('platform', 'name', toUInt64(v.platform_id)) AS platform_name,
                dictGet('organization', 'name', toUInt64(v.organization_id)) AS organization,
                dictGet('report_type', 'short_name', toUInt64(v.report_type_id))
                    AS report_type_short_name,
                dictGet('report_type', 'name', toUInt64(v.report_type_id)) AS report_type_name,
                dictGet('metric', 'short_name', toUInt64(v.metric_id)) AS metric,
                v.value as value,
                q.q[2] AS median,
                q.q[3] - q.q[1] AS iqr,
                q.q[1] - 5 * iqr AS lower_bound,
                q.q[3] + 5 * iqr AS upper_bound,
                q.num_values,
                round(
                    CASE
                        WHEN iqr = 0 AND median = 0 THEN 0
                        WHEN iqr = 0 AND median != 0 THEN
                            abs(toFloat64(v.value) - toFloat64(median))
                        WHEN v.value > q.q[3] THEN abs((v.value - q.q[3]) / iqr)
                        WHEN v.value < q.q[1] THEN abs((v.value - q.q[1]) / iqr)
                        ELSE 0
                    END
                ) AS significance,
                (v.value - q.q[2]) AS median_diff,
                abs(v.value - q.q[2]) AS abs_median_diff
            FROM cutoffs c
            JOIN {ZERO_FILL_VIEW_NAME} v
            ON v.date = c.cutoff_date
            JOIN quantiles_per_group q
            ON q.cutoff_date = c.cutoff_date
            AND q.platform_id = v.platform_id
            AND q.organization_id = v.organization_id
            AND q.report_type_id = v.report_type_id
            AND q.metric_id = v.metric_id
            WHERE 1
            AND (v.value < lower_bound OR v.value > upper_bound)
            AND report_type_short_name != 'interest'
            AND abs_median_diff > 30
            AND significance >= 5
            AND q.num_values > 8
            ORDER BY c.cutoff_date, platform_id, organization_id, report_type_id, metric_id, v.date
        """

        with self.backend.pool.get_client() as client:
            params = {"cutoff_date": self.month_from, "cutoff_date_to": self.month_to}
            if self.organization_ids:
                params["organization_ids"] = tuple(self.organization_ids)
            start = time.monotonic()
            rows, columns = client.execute(query, params, with_column_types=True)
            logger.debug(
                f"Clickhouse anomaly report query took {time.monotonic() - start:.2f} seconds"
            )
        column_names = [name for name, _ in columns]
        res = [dict(zip(column_names, row, strict=True)) for row in rows]
        # Add simple sequential ids 1..N
        for idx, r in enumerate(res, start=1):
            r["id"] = idx
            self.anomalies.append(
                AnomalySource(
                    anomaly_id=r["id"],
                    anomaly_date=r["date"],
                    platform_id=r["platform_id"],
                    organization_id=r["organization_id"],
                    report_type_id=r["report_type_id"],
                    metric_id=r["metric_id"],
                )
            )
        if len(self.anomalies) > 0:
            history_map = self._get_historical_data()
            for r in res:
                # Convert list of HistoryItem to dict {month_str: value}
                history_list = history_map.get(r["id"], [])
                r["history"] = {item.month.isoformat(): item.value for item in history_list}
        return res

    def get_anomaly_details(self, anomaly: AnomalySource):
        """
        Get details (reasons) for a single anomaly.
        """
        self.anomalies = [anomaly]
        title_map = self._get_title_data()
        dimension_map = self._get_dimension_data()
        reasons = []
        for item in title_map.get(anomaly.anomaly_id, []):
            reasons.append(item)
        for item in dimension_map.get(anomaly.anomaly_id, []):
            reasons.append(item)
        return {"reasons": reasons}
