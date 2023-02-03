from django.apps import AppConfig


class LogsConfig(AppConfig):
    name = 'logs'

    def ready(self):
        super().ready()
        from . import signals  # noqa - needed to register the signals
