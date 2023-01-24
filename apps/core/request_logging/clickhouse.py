import logging

from hcube.api.models.cube import Cube
from hcube.api.models.dimensions import (
    ArrayDimension,
    BooleanDimension,
    DateTimeDimension,
    IntDimension,
    IPv4Dimension,
    IPv6Dimension,
    MapDimension,
    StringDimension,
)
from hcube.api.models.metrics import FloatMetric, IntMetric
from hcube.backends.clickhouse import ClickhouseCubeBackend

logger = logging.getLogger(__name__)


class RequestLogCube(Cube):

    # we need some way how to globally store the backend instance, but we don't want to
    # create it on module import, because it would require django settings to be already
    # loaded
    # so the following class attribute is used to store the backend instance and is populated
    # on first use by the `get_logging_backend` function
    backend = None

    # model attributes
    hostname = StringDimension(clickhouse={'low_cardinality': True})
    db_server = StringDimension(clickhouse={'low_cardinality': True})
    clickhouse_db_server = StringDimension(clickhouse={'low_cardinality': True})
    timestamp = DateTimeDimension(clickhouse={"compression_codec": "Delta"})
    ipv4 = IPv4Dimension()
    ipv6 = IPv6Dimension()
    request_method = StringDimension(clickhouse={'low_cardinality': True})
    request_path = StringDimension(clickhouse={'low_cardinality': True})
    request_view = StringDimension(clickhouse={'low_cardinality': True})
    request_url_name = StringDimension(clickhouse={'low_cardinality': True})
    request_view_args = ArrayDimension(
        dimension=StringDimension(clickhouse={'low_cardinality': True})
    )
    request_view_kwargs = MapDimension(
        key_dimension=StringDimension(clickhouse={'low_cardinality': True}),
        value_dimension=StringDimension(clickhouse={'low_cardinality': True}),
    )
    request_query_params = MapDimension(
        key_dimension=StringDimension(clickhouse={'low_cardinality': True}),
        value_dimension=StringDimension(clickhouse={'low_cardinality': True}),
    )
    request_data = StringDimension()
    request_headers = MapDimension(
        key_dimension=StringDimension(clickhouse={'low_cardinality': True}),
        value_dimension=StringDimension(),
    )
    request_content_type = StringDimension(clickhouse={'low_cardinality': True})
    ref_path = StringDimension(clickhouse={'low_cardinality': True}, help_text='Referrer path')
    ref_query_params = MapDimension(
        key_dimension=StringDimension(clickhouse={'low_cardinality': True}),
        value_dimension=StringDimension(clickhouse={'low_cardinality': True}),
        help_test='Referrer query params',
    )
    response_status_code = IntDimension()
    user_id = IntDimension()
    user_email = StringDimension(clickhouse={'low_cardinality': True})
    user_username = StringDimension(clickhouse={'low_cardinality': True})
    user_is_staff = BooleanDimension()
    user_is_superuser = BooleanDimension()
    user_is_active = BooleanDimension()
    debug = BooleanDimension()
    # celus specific dimensions
    celus_version = StringDimension(clickhouse={'low_cardinality': True})
    celus_git_hash = StringDimension(clickhouse={'low_cardinality': True})
    clickhouse_query_active = BooleanDimension()
    # impersonification
    real_user_id = IntDimension(help_text='When impersonating, this is the real user')
    real_user_email = StringDimension(
        clickhouse={'low_cardinality': True}, help_text='When impersonating, this is the real user'
    )
    real_user_username = StringDimension(
        clickhouse={'low_cardinality': True}, help_text='When impersonating, this is the real user'
    )
    impersonified = BooleanDimension()
    # metrics
    query_count_django = IntMetric()
    query_count_clickhouse = IntMetric()
    request_size = IntMetric()
    response_size = IntMetric()
    execution_time = FloatMetric(help_text="Execution time in milliseconds")

    class Clickhouse:
        engine = "MergeTree"
        primary_key = ["hostname", "request_url_name", "celus_version", "timestamp"]
        sorting_key = [
            "hostname",
            "request_url_name",
            "celus_version",
            "timestamp",
            "request_method",
            "user_email",
        ]
        partition_key = ["toYYYYMM(timestamp)"]


RequestLogRecord = RequestLogCube.record_type()


def get_logging_backend():
    if RequestLogCube.backend:
        return RequestLogCube.backend

    from django.conf import settings

    RequestLogCube.backend = ClickhouseCubeBackend(
        database=settings.CLICKHOUSE_LOGGING_DB,
        user=settings.CLICKHOUSE_LOGGING_USER,
        password=settings.CLICKHOUSE_LOGGING_PASSWORD,
        host=settings.CLICKHOUSE_LOGGING_HOST,
        port=settings.CLICKHOUSE_LOGGING_PORT,
        secure=settings.CLICKHOUSE_LOGGING_SECURE,
    )
    return RequestLogCube.backend
