from datetime import date, timedelta

import pytest
from events.models import Event, EventImportance, UserEvent
from freezegun import freeze_time

from counter_registry.models import NotificationEvent
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


@pytest.mark.django_db
class TestRegistryNotificationsToEvents:
    @freeze_time("2025-06-01")
    def test_sync_events(self, registry_notification_models):
        assert NotificationEvent.objects.count() == 2
        assert Event.objects.filter(notificationevent__isnull=False).count() == 2
        assert Event.objects.filter(platform=registry_notification_models["platform"]).count() == 0
        NotificationEvent.objects.all().sync_events()
        assert NotificationEvent.objects.count() == 7
        assert Event.objects.filter(notificationevent__isnull=False).count() == 7
        assert Event.objects.filter(platform=registry_notification_models["platform"]).count() == 4

        events = list(Event.objects.order_by("created"))

        def plus_minus_day(date1, date2):
            assert date1 - timedelta(days=1) <= date2 <= date1 + timedelta(days=1), (
                "date not in range"
            )

        # rerun is performed
        NotificationEvent.objects.all().sync_events()
        assert NotificationEvent.objects.count() == 7, (
            "no other notification event is created on rerun"
        )
        assert Event.objects.filter(notificationevent__isnull=False).count() == 7, (
            "no other event is created on rerun"
        )

        assert "Affected" not in events[2].description
        assert events[2].importance == EventImportance.HIGH
        plus_minus_day(date(2025, 3, 1), events[2].created.date())
        plus_minus_day(date(2026, 3, 1), events[2].expiration_date.date())

        # check the full event description
        # event 3
        assert events[3].notificationevent.notification.sushi_service is None
        d3 = events[3].description
        assert "**Affected dates:** since" in d3
        assert "**Affected reports:**" not in d3
        assert "---" in d3
        assert "**Notification type:** Generic" in d3
        assert "**COUNTER version:**" not in d3, "no sushi service => no COUNTER version"

        assert events[3].importance == EventImportance.NORMAL
        plus_minus_day(date(2025, 4, 1), events[3].created.date())
        plus_minus_day(date(2026, 4, 1), events[3].expiration_date.date())

        # event 4
        assert events[4].notificationevent.notification.sushi_service is not None
        assert "**Affected dates:** until" in events[4].description
        assert "**Affected reports:**" not in events[4].description
        assert "---" in events[4].description
        assert "**Notification type:** Data Edit" in events[4].description
        assert "**COUNTER version:** 5.1" in events[4].description

        assert events[4].importance == EventImportance.HIGH, "data edit is high importance"
        plus_minus_day(date(2025, 5, 1), events[4].created.date())
        plus_minus_day(date(2026, 5, 1), events[4].expiration_date.date())

        # event 5
        assert "**Affected dates:**" in events[5].description
        assert "**Affected reports:** TR (R5)" in events[5].description
        assert events[5].importance == EventImportance.NORMAL
        plus_minus_day(date(2025, 6, 1), events[5].created.date())
        plus_minus_day(date(2026, 6, 1), events[5].expiration_date.date())

        assert "**Affected dates:**" not in events[6].description
        assert "**Affected reports:** IR (R5.1)" in events[6].description
        assert events[6].importance == EventImportance.NORMAL
        plus_minus_day(date(2025, 7, 1), events[6].created.date())
        plus_minus_day(date(2026, 7, 1), events[6].expiration_date.date())

    @pytest.mark.parametrize(
        "freezed,count",
        (
            ("2025-05-01", 3),  # 2 for su and 1 for admin1
            ("2026-01-15", 2),  # 1 for su and 1 for admin1 (one too old)
        ),
    )
    def test_assign_to_users(self, registry_notification_models, freezed, count):
        assert UserEvent.objects.count() == 0

        with freeze_time(freezed):
            NotificationEvent.objects.all().assign_to_users()

        assert UserEvent.objects.count() == count
