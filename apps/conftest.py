import re

import pytest
from clickhouse_driver import Client
from filelock import FileLock
from logs.cubes import AccessLogCube, ch_backend
from logs.logic.clickhouse import initialize_clickhouse


def get_client(settings):
    database = settings.CLICKHOUSE_DB
    user = settings.CLICKHOUSE_USER
    password = settings.CLICKHOUSE_PASSWORD
    host = settings.CLICKHOUSE_HOST
    port = settings.CLICKHOUSE_PORT
    secure = settings.CLICKHOUSE_SECURE
    client = Client(
        database=database, host=host, port=port, user=user, password=password, secure=secure
    )
    return client


def clickhouse_raw_connection(request, settings):
    """
    pytest fixture which prepares a clickhouse connection if param `clickhouse_on` is given,
    or adjust settings for clickhouse being disabled if `clickhouse_off` is given
    """
    if request.param == "clickhouse_on":
        # enforce the settings to make sure it is independent of current environment
        settings.CLICKHOUSE_SYNC_ACTIVE = True
        settings.CLICKHOUSE_QUERY_ACTIVE = True
        with FileLock("clickhouse.lock").acquire():
            client = get_client(settings)
            yield client
    else:
        settings.CLICKHOUSE_SYNC_ACTIVE = False
        settings.CLICKHOUSE_QUERY_ACTIVE = False
        yield


def clickhouse_connection(request, settings):
    """
    pytest fixture which creates and then destroys the test table
    """
    if request.param == "clickhouse_on":
        # enforce the settings to make sure it is independent of current environment
        settings.CLICKHOUSE_SYNC_ACTIVE = True
        settings.CLICKHOUSE_QUERY_ACTIVE = True
        with FileLock("clickhouse.lock").acquire():
            client = get_client(settings)
            ch_backend.drop_storage(AccessLogCube)
            initialize_clickhouse()
            yield client
            ch_backend.drop_storage(AccessLogCube)
    else:
        settings.CLICKHOUSE_SYNC_ACTIVE = False
        settings.CLICKHOUSE_QUERY_ACTIVE = False
        yield


clickhouse_on_off = pytest.fixture(params=["clickhouse_on", "clickhouse_off"])(
    clickhouse_connection
)

clickhouse_db = pytest.fixture(params=["clickhouse_on"])(clickhouse_connection)

clickhouse_raw_on_off = pytest.fixture(params=["clickhouse_on", "clickhouse_off"])(
    clickhouse_raw_connection
)


@pytest.fixture()
def inmemory_media(settings):
    settings.DEFAULT_FILE_STORAGE = "inmemorystorage.InMemoryStorage"


@pytest.fixture(autouse=True)
def isolated_cache_in_parallel_test_run(worker_id, settings):
    # worker_id is a fixture from pytest-dist
    # it contains "master" when no parallel run is performed
    # "gw0", "gw1", ... when running in parallel

    if worker_id == "master":
        return  # tests are not running in parallel => no extra handling required

    # cache versions should be numbers so the number is extracted from from "gwX"
    worker_number = int(re.search(r"\d+$", worker_id).group(0))

    # there are incr_version() and decr_version() methods in django which can be used
    # to decrease / increase version of a key
    # in order to avoid version overlaps the number is multiplied e.g. 1 -> 1000
    cache_version = (worker_number + 1) * 1000

    for name in settings.CACHES.keys():
        settings.CACHES[name]["VERSION"] = cache_version

    # force cache reinitialization
    from django.test.signals import clear_cache_handlers

    clear_cache_handlers(setting="CACHES")


# Counter registry tests configuration
def pytest_addoption(parser):
    parser.addoption(
        "--counter-registry",
        action="store_true",
        dest="counter_registry",
        default=False,
        help="run counter_registry tests",
    )


def pytest_configure(config):
    if config.option.counter_registry:
        if markexpr := getattr(config.option, "markexpr", None):
            config.option.markexpr = markexpr + " and counter_registry"
        else:
            config.option.markexpr = "counter_registry"
    else:
        if markexpr := getattr(config.option, "markexpr", None):
            config.option.markexpr = markexpr + " and not counter_registry"
        else:
            config.option.markexpr = "not counter_registry"
