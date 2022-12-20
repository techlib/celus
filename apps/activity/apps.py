from django.apps import AppConfig


class ActivityConfig(AppConfig):
    name = 'activity'

    def ready(self):
        from . import signals  # noqa - this is necessary to run the code in the module
