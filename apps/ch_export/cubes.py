from typing import Optional

from clickhouse_driver import Client
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from hcube.backends.clickhouse import ClickhouseCubeBackend
from logs.logic.export_analytical.exports.hcube import assert_valid_identifier, sanitize_identifier

ch_export_client: Optional[Client] = None
if settings.CLICKHOUSE_EXPORT_HOST:
    ch_export_client = Client(
        user=settings.CLICKHOUSE_EXPORT_USER,
        password=settings.CLICKHOUSE_EXPORT_PASSWORD,
        host=settings.CLICKHOUSE_EXPORT_HOST,
        port=settings.CLICKHOUSE_EXPORT_PORT,
        secure=settings.CLICKHOUSE_EXPORT_SECURE,
        verify=settings.CLICKHOUSE_EXPORT_VERIFY,
    )


def ch_export_database_prefix() -> str:
    return sanitize_identifier("export_" + settings.DATABASES["default"]["NAME"])


def create_ch_export_database(db: str) -> ClickhouseCubeBackend:
    if not ch_export_client:
        raise ImproperlyConfigured("Clickhouse export backend is not configured")
    assert_valid_identifier(db)
    ch_export_client.execute(
        "CREATE DATABASE IF NOT EXISTS {db:Identifier}",
        {"db": db},
        settings={"server_side_params": True},
    )


def create_ch_export_backend(db: str) -> ClickhouseCubeBackend:
    return ClickhouseCubeBackend(
        database=db,
        user=settings.CLICKHOUSE_EXPORT_USER,
        password=settings.CLICKHOUSE_EXPORT_PASSWORD,
        host=settings.CLICKHOUSE_EXPORT_HOST,
        port=settings.CLICKHOUSE_EXPORT_PORT,
        secure=settings.CLICKHOUSE_EXPORT_SECURE,
        verify=settings.CLICKHOUSE_EXPORT_VERIFY,
    )


def create_ch_export_user(db: str, username: str, password: str) -> str:
    if not ch_export_client:
        raise ImproperlyConfigured("Clickhouse export backend is not configured")
    assert_valid_identifier(db)
    assert_valid_identifier(username)
    ch_export_client.execute(
        "CREATE USER OR REPLACE %(username)s IDENTIFIED BY %(password)s",
        {"username": username, "password": password},
    )
    ch_export_client.execute(f"GRANT SELECT ON {db}.* TO {username}")
    return password
