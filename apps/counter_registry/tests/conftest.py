import pytest
from publications import fake_data as publications_fake_data
from sushi import fake_data as sushi_fake_data

from counter_registry.fake_data import (
    CounterRegistryProfileFactory,
    NotificationEventFactory,
    NotificationFactory,
    PlatformExtrasFactory,
    ReportFactory,
    SushiServiceFactory,
)
from counter_registry.models import Platform
from test_scenarios.basic import (  # noqa
    basic1,
    clients,
    counter_report_types,
    data_sources,
    identities,
    organizations,
    platforms,
    report_types,
    users,
)


@pytest.fixture
def registry_platform_models(counter_report_types):
    # make registry models
    jr1 = ReportFactory(counter_release=4, report_id="JR1")
    tr = ReportFactory(counter_release=5, report_id="TR")
    dr = ReportFactory(counter_release=5, report_id="DR")
    ir = ReportFactory(counter_release=51, report_id="IR")
    p1 = PlatformExtrasFactory(
        platform__id="88888888-8888-8888-8888-888888888888",
        platform__name="Plat1",
        platform__abbrev="P1",
        platform__content_provider_name="PROVIDER",
        platform__website="https://platform.example.url/",
    )
    p2 = PlatformExtrasFactory(platform__name="Plat2")
    p2.notes = "some notes"  # setting notes via PlatformExtrasFactory doesn't work...
    p2.save()
    SushiServiceFactory(
        platform=p1.platform, counter_release=5, url="https://www.example.com/sushi5"
    )
    SushiServiceFactory(
        platform=p1.platform, counter_release=51, url="https://www.example.com/sushi51"
    )
    SushiServiceFactory(
        platform=p2.platform, counter_release=4, url="https://www.example.com/sushi4"
    )
    p1.platform.reports.add(tr)
    p1.platform.reports.add(dr)
    p1.platform.reports.add(ir)
    p2.platform.reports.add(jr1)
    Platform.objects.all().sync_knowledgebase()
    p1.refresh_from_db()
    p2.refresh_from_db()

    # make celus models
    pc = publications_fake_data.PlatformFactory(
        counter_registry_id=p1.platform.id,
        provider="PROVIDER",
        counter_reports_source="knowledgebase",
    )
    pc.counter_reports.add(counter_report_types["br1"])
    creds = sushi_fake_data.CredentialsFactory(
        counter_version=5, platform=pc, use_counter_reports_from_platform=True, auto_update_url=True
    )
    creds.counter_reports.add(counter_report_types["pr"])

    return locals()


@pytest.fixture
def registry_notification_models(users):
    # disable events_from_counter_registry for all users

    platform = publications_fake_data.PlatformFactory(
        counter_registry_id="99999999-9999-9999-9999-999999999999"
    )
    # existing notification event
    NotificationEventFactory(
        event__created="2025-01-01",
        event__expiration_date="2026-01-01",
        notification__published_date="2025-01-01",
    )
    NotificationEventFactory(
        event__created="2025-02-01",
        event__expiration_date="2026-02-01",
        notification__published_date="2025-02-01",
    )

    # notifications
    NotificationFactory(
        sushi_service__platform__id=platform.counter_registry_id,
        published_date="2025-03-01",
        start_date=None,
        end_date=None,
        message="AAAA",
        type="DATA EDIT",
    )
    NotificationFactory(
        sushi_service=None,
        published_date="2025-04-01",
        message="BBBB",
        start_date="2024-08-01",
        end_date=None,
        type="GENERIC",
    )
    NotificationFactory(
        sushi_service__platform__id=platform.counter_registry_id,
        sushi_service__counter_release=51,
        published_date="2025-05-01",
        message="CCCC",
        start_date=None,
        end_date="2024-09-01",
        type="DATA EDIT",
    )
    NotificationFactory(
        sushi_service__platform__id=platform.counter_registry_id,
        published_date="2025-06-01",
        message="DDDD",
        start_date="2024-10-01",
        end_date="2024-11-01",
        reports=[{"counter_release": "5", "report_id": "TR"}],
        type="GENERIC",
    )
    NotificationFactory(
        sushi_service__platform__id=platform.counter_registry_id,
        published_date="2025-07-01",
        message="EEEE",
        start_date=None,
        end_date=None,
        reports=[{"counter_release": "5.1", "report_id": "IR"}],
        type="GENERIC",
    )

    for key, user in users.items():
        if key == "su":
            # profile enabled without last
            profile_enabled_without_last = CounterRegistryProfileFactory(
                user=user, last_registry_event_date=None
            )

        elif key == "admin1":
            # profile enabled without last
            profile_enabled_with_last = CounterRegistryProfileFactory(
                events_from_counter_registry=True,  # defaut is True
                user=user,
                last_registry_event_date="2025-01-15",
            )
        else:
            CounterRegistryProfileFactory(
                events_from_counter_registry=False, user=user, last_registry_event_date="2025-01-15"
            )

    return locals()
