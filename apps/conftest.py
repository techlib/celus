import pytest
from clickhouse_driver import Client
from filelock import FileLock
from logs.cubes import AccessLogCube, ch_backend


def clickhouse_connection(request, settings):
    """
    pytest fixture which creates and then destroys the test database
    """
    if request.param == 'clickhouse_on':
        # enforce the settings to make sure it is independent of current environment
        settings.CLICKHOUSE_SYNC_ACTIVE = True
        settings.CLICKHOUSE_QUERY_ACTIVE = True
        with FileLock("clickhouse.lock").acquire():
            database = settings.CLICKHOUSE_DB
            user = settings.CLICKHOUSE_USER
            password = settings.CLICKHOUSE_PASSWORD
            host = settings.CLICKHOUSE_HOST
            port = settings.CLICKHOUSE_PORT
            secure = settings.CLICKHOUSE_SECURE
            client = Client(
                database=database, host=host, port=port, user=user, password=password, secure=secure
            )

            ch_backend.drop_storage(AccessLogCube)
            ch_backend.initialize_storage(AccessLogCube)
            yield client
            ch_backend.drop_storage(AccessLogCube)
    else:
        settings.CLICKHOUSE_SYNC_ACTIVE = False
        settings.CLICKHOUSE_QUERY_ACTIVE = False
        yield


clickhouse_on_off = pytest.fixture(params=['clickhouse_on', 'clickhouse_off'])(
    clickhouse_connection
)

clickhouse_db = pytest.fixture(params=['clickhouse_on'])(clickhouse_connection)


@pytest.fixture()
def inmemory_media(settings):
    settings.DEFAULT_FILE_STORAGE = 'inmemorystorage.InMemoryStorage'
