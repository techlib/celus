from collections import Counter as CounterDict

from django.conf import settings
from django.core.cache import cache
from django.db.models import BooleanField, Count, Exists, ExpressionWrapper, F, OuterRef, Q
from django_prometheus.conf import NAMESPACE
from django_prometheus.middleware import (
    Metrics,
    PrometheusAfterMiddleware,
    PrometheusBeforeMiddleware,
)
from prometheus_client import Counter, Gauge, Summary

report_access_total_counter = Counter(
    "celus_report_access_total",
    "The number of times a report type was accessed from a specific type of view. Also "
    "split by report type",
    ["view_type", "report_type"],
)

report_access_time_summary = Summary(
    "celus_report_access_time_seconds",
    "The time it took to process request for data for each report type. Also split by view_type",
    ["view_type", "report_type"],
)

celus_version_num = Gauge(
    "celus_version_num",
    "CELUS version converted to int. For example 4.1.2 => 40102",
    [],
    multiprocess_mode="livemax",
)

celus_sentry_release = Gauge(
    "celus_git_hash",
    "In production this is a git hash of deployed commit. It is stored in the hash dimension. "
    "Value is always 1",
    ["hash"],
    multiprocess_mode="livemax",
)


def db_access_log_num():
    if settings.CLICKHOUSE_SYNC_ACTIVE:
        from hcube.api.models.aggregation import Count as HCount
        from logs.cubes import AccessLogCube, ch_backend

        return ch_backend.get_one_record(AccessLogCube.query().aggregate(count=HCount())).count
    else:
        return 0  # we do not query postgres for this as it is too slow


def db_import_batch_num():
    from logs.models import ImportBatch

    return ImportBatch.objects.count()


def db_credentials_num():
    from sushi.models import SushiCredentials

    return {
        (rec["counter_version"], rec["enabled"], rec["broken"] or "", rec["verified"]): rec["count"]
        for rec in SushiCredentials.objects.annotate_verified()
        .values("counter_version", "enabled", "broken", "verified")
        .annotate(count=Count("id"))
    }


def db_organization_num():
    from organizations.models import Organization

    return Organization.objects.count()


def db_user_num():
    from organizations.models import UserOrganization

    from core.models import User

    counter = CounterDict()
    for user in User.objects.all().annotate(
        is_admin=Exists(UserOrganization.objects.filter(user_id=OuterRef("id"), is_admin=True))
    ):
        perm_type = "superuser" if user.is_superuser else "org_admin" if user.is_admin else "normal"
        counter[(perm_type,)] += 1
    return counter


def db_title_num():
    from publications.models import Title

    return Title.objects.count()


def db_platform_num():
    from publications.models import Platform

    from core.models import DataSource

    out = {}
    for rec in (
        Platform.objects.all()
        .order_by()
        .annotate(source_type=F("source__type"))
        .values("source_type")
        .annotate(count=Count("id"))
    ):
        source_type_name = (
            next(name for t, name in DataSource.TYPE_CHOICES if t == rec["source_type"])
            if rec["source_type"]
            else "local"
        )
        out[(source_type_name,)] = rec["count"]
    return out


def db_mdu_num():
    from logs.models import ManualDataUpload

    return {
        (rec["method"],): rec["count"]
        for rec in ManualDataUpload.objects.values("method").annotate(count=Count("id"))
    }


def db_reporting_reports_num():
    from logs.models import FlexibleReport

    counter = CounterDict()
    for report in FlexibleReport.objects.all():
        counter[(report.access_level.name,)] += 1
    return counter


def db_recached_queries_num():
    from recache.models import CachedQuery

    return {
        (rec["origin"],): rec["count"]
        for rec in CachedQuery.objects.values("origin").annotate(count=Count("id"))
    }


def db_fetch_intentions_num():
    from scheduler.models import FetchIntention

    return {
        (rec["processed"],): rec["count"]
        for rec in FetchIntention.objects.annotate(
            processed=ExpressionWrapper(
                Q(when_processed__isnull=False), output_field=BooleanField()
            )
        )
        .values("processed")
        .annotate(count=Count("id"))
    }


def db_fetch_attempts_num():
    from sushi.models import SushiFetchAttempt

    return {
        (rec["processed"],): rec["count"]
        for rec in SushiFetchAttempt.objects.annotate(
            processed=ExpressionWrapper(Q(import_batch__isnull=False), output_field=BooleanField())
        )
        .values("processed")
        .annotate(count=Count("id"))
    }


def db_tag_classes_num():
    from tags.models import TagClass

    return TagClass.objects.count()


def db_tags_num():
    from tags.models import Tag

    return Tag.objects.count()


def _db_last_two_years_coverage_data():
    """
    This is a helper function used by several metrics.
    :return:
    """
    from datetime import timedelta

    from logs.logic.data_coverage import DataCoverageExtractor
    from logs.models import ImportBatch, ReportType

    from core.logic.dates import last_month, month_start

    # the end date should be the one month before the last finished month
    # the start date should cover the year of the end date + previous two full years
    end_month = month_start(last_month() - timedelta(days=1))
    start_month = end_month.replace(year=end_month.year - 2, month=1, day=1)

    rt_qs = ReportType.objects.exclude_materialized().filter(
        Q(
            Exists(
                ImportBatch.objects.filter(
                    report_type_id=OuterRef("pk"), date__gte=start_month, date__lte=end_month
                )
            )
        )
    )

    totals = CounterDict()
    for rt in rt_qs:
        extractor = DataCoverageExtractor(
            rt,
            start_month=start_month,
            end_month=end_month,
            split_by_org=False,
            split_by_platform=False,
            split_by_date=False,
        )
        cov_data = extractor.get_coverage_data()
        if cov_data:
            data = cov_data[()]  # empty tuple key because we don't split
            totals["ib_count"] += data["ib_count"]
            totals["ib_max"] += data["ib_max"]

    totals["ratio"] = (totals["ib_count"] / totals["ib_max"]) if totals["ib_max"] else 0
    return totals


def db_last_two_years_coverage():
    """
    Because `_db_last_two_years_coverage_data` is a slow function, we store the results in the
    cache to be available for other metrics. These should be evaluated just after each other,
    so the cache should be valid. Using a short timeout switches the cache to a temporary
    storage rather than a real cache.
    :return:
    """
    cached = cache.get("_db_last_two_years_coverage_data")
    if cached:
        return cached["ratio"]
    totals = _db_last_two_years_coverage_data()
    cache.set("_db_last_two_years_coverage_data", totals, 10)
    return totals["ratio"]


def db_last_two_years_coverage_present_ib_count():
    cached = cache.get("_db_last_two_years_coverage_data")
    if cached:
        return cached["ib_count"]
    totals = _db_last_two_years_coverage_data()
    cache.set("_db_last_two_years_coverage_data", totals, 10)
    return totals["ib_count"]


def db_last_two_years_coverage_expected_ib_count():
    cached = cache.get("_db_last_two_years_coverage_data")
    if cached:
        return cached["ib_max"]
    totals = _db_last_two_years_coverage_data()
    cache.set("_db_last_two_years_coverage_data", totals, 10)
    return totals["ib_max"]


def db_events_by_category_and_importance():
    from events.models import Event

    return {
        (rec["category"], rec["importance"]): rec["count"]
        for rec in Event.objects.values("category", "importance").annotate(count=Count("id"))
    }


# The following metrics will not be updated by any request, but by a celery based task.
# This makes it possible to decide on any interval how often we want to update the metrics.
# To get the data into Django, we store it in the cache and then pick it up in the
# PrometheusAfterMiddleware.
CACHE_STORED_GAUAGES = {
    # we use clickhouse in the following because the table is large and query to the postgres
    # database is very slow
    "celus_db_access_log_num": {
        "desc": "Number of access logs in the clickhouse database",
        "func": db_access_log_num,
    },
    "celus_db_import_batch_num": {
        "desc": "Number of import batches in the database",
        "func": db_import_batch_num,
    },
    "celus_db_credentials_num": {
        "desc": "Number of credentials in the database",
        "dims": ["counter_version", "is_active", "broken", "verified"],
        "func": db_credentials_num,
    },
    "celus_db_organization_num": {
        "desc": "Number of organizations in the database",
        "func": db_organization_num,
    },
    "celus_db_user_num": {
        "desc": "Number of users in the database",
        "dims": ["permission_type"],
        "func": db_user_num,
    },
    "celus_db_title_num": {"desc": "Number of titles in the database", "func": db_title_num},
    "celus_db_platform_num": {
        "desc": "Number of platforms in the database",
        "dims": ["source_type"],
        "func": db_platform_num,
    },
    "celus_db_mdu_num": {
        "desc": "Number of MDUs in the database",
        "dims": ["method"],
        "func": db_mdu_num,
    },
    "celus_db_reporting_reports_num": {
        "desc": "Number of reports in the database",
        "dims": ["access_level"],
        "func": db_reporting_reports_num,
    },
    "celus_db_recached_queries_num": {
        "desc": "Number of recached queries in the database",
        "dims": ["origin"],
        "func": db_recached_queries_num,
    },
    "celus_db_fetch_intentions_num": {
        "desc": "Number of fetch intentions in the database",
        "dims": ["processed"],
        "func": db_fetch_intentions_num,
    },
    "celus_db_fetch_attempts_num": {
        "desc": "Number of fetch attempts in the database",
        "dims": ["successfull"],
        "func": db_fetch_attempts_num,
    },
    "celus_db_tag_classes_num": {
        "desc": "Number of tag classes in the database",
        "func": db_tag_classes_num,
    },
    "celus_db_tags_num": {"desc": "Number of tags in the database", "func": db_tags_num},
    "celus_db_last_two_years_coverage": {
        "desc": "Overall coverage of the last two years for the whole consortium",
        "func": db_last_two_years_coverage,
    },
    "celus_db_last_two_years_coverage_present_ib_count": {
        "desc": "Number of present IBs in the last two years for the whole consortium",
        "func": db_last_two_years_coverage_present_ib_count,
    },
    "celus_db_last_two_years_coverage_expected_ib_count": {
        "desc": "Number of expected IBs in the last two years for the whole consortium",
        "func": db_last_two_years_coverage_expected_ib_count,
    },
    "celus_db_events_num": {
        "desc": "Number of events in the database",
        "dims": ["category", "importance"],
        "func": db_events_by_category_and_importance,
    },
}


class CelusMetrics(Metrics):
    def register(self):
        super().register()
        self.cached_gauges = {}
        for name, params in CACHE_STORED_GAUAGES.items():
            dims = params.get("dims", [])
            desc = params["desc"]
            self.cached_gauges[name] = self.register_metric(
                Gauge, name, desc, dims, namespace=NAMESPACE, multiprocess_mode="livemax"
            )


class CelusPrometheusBeforeMiddleware(PrometheusBeforeMiddleware):
    metrics_cls = CelusMetrics


class CelusPrometheusAfterMiddleware(PrometheusAfterMiddleware):
    metrics_cls = CelusMetrics

    def process_request(self, request):
        super().process_request(request)
        for name, params in CACHE_STORED_GAUAGES.items():
            dims = params.get("dims", [])
            value = cache.get(name, {} if dims else 0)
            if dims:
                for labels, val in value.items():
                    self.metrics.cached_gauges[name].labels(*labels).set(val)
            else:
                self.metrics.cached_gauges[name].set(value)
