from django.apps import AppConfig


class LogsConfig(AppConfig):
    name = 'logs'

    def ready(self):
        super().ready()
        # noinspection PyUnresolvedReferences
        from . import signals  # needed to register the signals
