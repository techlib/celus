from django.apps import AppConfig
from django.conf import settings


class LogsConfig(AppConfig):
    name = 'logs'

    def ready(self):
        super().ready()
        from . import signals  # noqa - needed to register the signals

        if settings.CLICKHOUSE_SYNC_ACTIVE or settings.CLICKHOUSE_QUERY_ACTIVE:
            from .logic.clickhouse import initialize_clickhouse

            initialize_clickhouse()
