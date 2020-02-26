from django.apps import AppConfig


class ActivityConfig(AppConfig):
    name = 'activity'

    def ready(self):
        from . import signals  # this is necessary to run the code in the module
