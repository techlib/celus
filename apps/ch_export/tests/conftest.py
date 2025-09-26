import pytest

from ch_export.cubes import ch_export_client, ch_export_database_prefix


@pytest.fixture
def ch_export_clickhouse():
    """
    This fixture makes sure that before each test, the Clickhouse export database
    is dropped, so that it does not interfere with other tests.

    Because the databases are created on the fly and their names depend on the organization
    primary key, we simply drop all databases that start with the prefix that is
    guaranteed to be the one used in the tests.
    """
    prefix = ch_export_database_prefix()
    dbs = ch_export_client.execute(
        "SELECT name, comment FROM system.databases WHERE startsWith(name, %(prefix)s)",
        {"prefix": prefix},
    )
    for db in dbs:
        ch_export_client.execute(f'DROP DATABASE IF EXISTS "{db[0]}"')
