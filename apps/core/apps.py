from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig
from django.core.checks import Error, Warning, register


class CelusAdminConfig(AdminConfig):
    default_site = "core.admin_site.CelusAdminSite"


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
    parts = version.split(".")
    result = 0
    for i, part in enumerate(reversed(parts)):
        try:
            x = int(part)
            result += x * 100**i
        except ValueError:
            pass
    return result


class CoreConfig(AppConfig):
    name = "core"

    def ready(self):
        super().ready()
        # noinspection PyUnresolvedReferences
        from django.conf import settings

        # noinspection PyUnresolvedReferences
        from . import (
            db,  # noqa - needed to register the ilike lookup
            signals,  # noqa - needed to register the signals
        )

        @register()
        def check_exposed_commands(app_configs, **kwargs):
            from .logic.management_commands import CommandManager

            errors = []
            for app, command in CommandManager.get_invalid_exposed_commands():
                errors.append(
                    Warning(f"Exposed command {app}.{command} is not available", id="core.W001")
                )
            return errors

        @register()
        def check_clickhouse_settings(app_configs, **kwargs):
            if settings.CLICKHOUSE_QUERY_ACTIVE and not settings.CLICKHOUSE_SYNC_ACTIVE:
                return [
                    Warning(
                        "Having `CLICKHOUSE_QUERY_ACTIVE` without `CLICKHOUSE_SYNC_ACTIVE` is "
                        "likely an error as the data will not be up to date in queries.",
                        id="core.W002",
                    )
                ]
            return []

        @register()
        def check_customer_care_admins(app_configs, **kwargs):
            if not all(
                isinstance(a, (list, tuple)) and len(a) == 2 for a in settings.CUSTOMER_CARE_ADMINS
            ):
                return [
                    Error(
                        "The CUSTOMER_CARE_ADMINS setting must be a list of 2-tuples.",
                        id="core.E001",
                    )
                ]
            return []

        @register()
        def check_eduid_and_otp(app_configs, **kwargs):
            if settings.ALLOW_EDUID_LOGIN and settings.OTP_ENABLED and not settings.TESTING:
                # in testing we allow both to be enabled because some tests require
                # OTP_ENABLED and some rely on ALLOW_EDUID_LOGIN
                return [
                    Error(
                        "Both EDUID (ALLOW_EDUID_LOGIN) and OTP (OTP_ENABLED) are enabled. "
                        "This is not supported.",
                        id="core.E002",
                    )
                ]
            return []
