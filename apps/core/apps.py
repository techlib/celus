from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        super().ready()
        # noinspection PyUnresolvedReferences
        from . import db  # needed to register the ilike lookup
