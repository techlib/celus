from django.apps import AppConfig


class ExportConfig(AppConfig):
    name = 'export'

    def ready(self):
        from . import signals  # noqa
