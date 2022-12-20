from django.apps import AppConfig


def version_to_int(version: str):
    """
    >>> version_to_int('3.2.1')
    30201

    >>> version_to_int('30.2.1')
    300201

    >>> version_to_int('2.1')
    201

    >>> version_to_int('2.x.1')
    20001

    >>> version_to_int('4.10.25')
    41025
    """
    parts = version.split('.')
    result = 0
    for i, part in enumerate(reversed(parts)):
        try:
            x = int(part)
            result += x * 100**i
        except ValueError:
            pass
    return result


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        super().ready()
        # noinspection PyUnresolvedReferences
        from django.conf import settings

        # noinspection PyUnresolvedReferences
        from . import db  # needed to register the ilike lookup
        from . import signals  # needed to register the signals
        from .prometheus import celus_sentry_release, celus_version_num

        celus_version_num.set(version_to_int(settings.CELUS_VERSION))
        celus_sentry_release.labels(hash=settings.SENTRY_RELEASE).set(1.0)
