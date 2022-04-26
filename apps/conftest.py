import os
import pytest

from clickhouse_driver import Client
from distutils.util import strtobool
from filelock import FileLock

from logs.cubes import ch_backend


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
            client = Client(host=host, port=port, user=user, password=password, secure=secure)

            if strtobool(os.environ.get("CLICKHOUSE_PURGE_TEST_DB", "False")):
                client.execute(f"DROP DATABASE IF EXISTS {database}")
                # update the backend to know that all tables were removed
                ch_backend._table_exists = {}
            elif (
                len(
                    client.execute(
                        "SELECT * FROM system.databases WHERE name=%(database)s;", locals()
                    )
                )
                > 0
            ):
                raise ValueError(
                    f'The database {database} already exists, to prevent loss of data due to '
                    'accidentally using production database for testing, we raise this error. '
                    'If the database name is correct, just drop the database and the tests will '
                    'recreate it.'
                )
            client.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
            yield client
            client.execute(f"DROP DATABASE IF EXISTS {database}")
            # update the backend to know that all tables were removed
            ch_backend._table_exists = {}
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
