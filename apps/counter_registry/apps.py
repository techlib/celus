from django.apps import AppConfig


class CounterRegistryConfig(AppConfig):
    name = "counter_registry"
    verbose_name = "Counter Registry"

    def ready(self):
        from . import signals  # noqa
