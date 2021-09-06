from django.apps import AppConfig


class KnowledgebaseConfig(AppConfig):
    name = 'knowledgebase'

    def ready(self):
        from . import signals  # noqa
