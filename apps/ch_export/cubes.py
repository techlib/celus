from typing import Optional

from clickhouse_driver import Client
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from hcube.api.models.cube import Cube
from hcube.api.models.dimensions import IntDimension, StringDimension
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


class TitleTagCube(Cube):
    title_id = IntDimension(signed=False, bits=32)
    tag_id = IntDimension(signed=False, bits=32)
    tag__name = StringDimension(clickhouse={"low_cardinality": True})
    tag_class_id = IntDimension(signed=False, bits=32)
    tag_class__name = StringDimension(clickhouse={"low_cardinality": True})

    class Clickhouse:
        table_name = "title_tags"
        primary_key = ["tag_class_id", "tag_id", "title_id"]
        sorting_key = ["tag_class_id", "tag_id", "title_id"]
        engine = "MergeTree"
        use_lightweight_deletes = True


class OrganizationTagCube(Cube):
    organization_id = IntDimension(signed=False, bits=32)
    tag_id = IntDimension(signed=False, bits=32)
    tag__name = StringDimension(clickhouse={"low_cardinality": True})
    tag_class_id = IntDimension(signed=False, bits=32)
    tag_class__name = StringDimension(clickhouse={"low_cardinality": True})

    class Clickhouse:
        table_name = "organization_tags"
        primary_key = ["tag_class_id", "tag_id", "organization_id"]
        sorting_key = ["tag_class_id", "tag_id", "organization_id"]
        engine = "MergeTree"
        use_lightweight_deletes = True


class PlatformTagCube(Cube):
    platform_id = IntDimension(signed=False, bits=32)
    tag_id = IntDimension(signed=False, bits=32)
    tag__name = StringDimension(clickhouse={"low_cardinality": True})
    tag_class_id = IntDimension(signed=False, bits=32)
    tag_class__name = StringDimension(clickhouse={"low_cardinality": True})

    class Clickhouse:
        table_name = "platform_tags"
        primary_key = ["tag_class_id", "tag_id", "platform_id"]
        sorting_key = ["tag_class_id", "tag_id", "platform_id"]
        engine = "MergeTree"
        use_lightweight_deletes = True
