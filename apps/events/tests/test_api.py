import pytest
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time

from events.fake_data import EventFactory, UserEventFactory
from events.models import (
    EventCategory,
    EventImportance,
    HandlingMethod,
    UserEvent,
    UserEventCategoryHandling,
)


@pytest.mark.django_db
class TestEventListAPI:
    @pytest.mark.parametrize("read", (True, False))
    def test_user_events_list_basic(self, admin_client, admin_user, read):
        """
        Tests that the user events list endpoint works as expected.
        """
        UserEvent.objects.all().delete()  # make sure that no user events exist
        event = EventFactory.create()
        event.assign_to_users([admin_user], read=read)
        response = admin_client.get("/api/events/user-events/")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        e1 = data["results"][0]
        assert e1["pk"] == event.pk
        assert e1["title"] == event.title
        assert e1["description"] == event.description
        assert e1["importance"] == event.importance
        assert e1["category"] == event.category
        assert (
            e1["created"] == event.created.astimezone(timezone.get_current_timezone()).isoformat()
        )
        assert e1["read"] is read

    def test_user_events_list_full(self, admin_client, admin_user, django_assert_max_num_queries):
        """
        Tests data returned by the user events list endpoint.
        """
        UserEvent.objects.all().delete()  # make sure that no user events exist
        events_connected = EventFactory.create_batch(10)
        EventFactory.create_batch(11)
        for e in events_connected:
            e.assign_to_users([admin_user])

        with django_assert_max_num_queries(9):
            response = admin_client.get(reverse("user-events-list"))
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 10
        assert len(data["results"]) == 10
        assert all(e.pk in [rec["pk"] for rec in data["results"]] for e in events_connected)

    @pytest.mark.parametrize(
        ["importance", "count"],
        [
            (EventImportance.NORMAL, 3),
            (EventImportance.HIGH, 5),
            (None, 8),
        ],
    )
    def test_user_events_list_filtering_importance(
        self, admin_client, admin_user, importance, count
    ):
        """
        Tests filtering by event importance.
        """
        UserEvent.objects.all().delete()  # make sure that no user events exist
        info_events = EventFactory.create_batch(3, importance=EventImportance.NORMAL)
        error_events = EventFactory.create_batch(5, importance=EventImportance.HIGH)
        EventFactory.create_batch(7)  # these are unconnected events, just to make sure
        for e in info_events + error_events:
            e.assign_to_users([admin_user])

        response = admin_client.get(
            reverse("user-events-list"),
            {"importance": importance} if importance else None,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == count
        assert len(data["results"]) == count
        if importance:
            assert all(rec["importance"] == importance for rec in data["results"])

    @pytest.mark.parametrize(
        ["category", "count"],
        [
            (EventCategory.SUSHI, 3),
            (EventCategory.TAGS, 5),
            (EventCategory.OVERLAP, 0),
            (None, 8),
        ],
    )
    def test_user_events_list_filtering_category(self, admin_client, admin_user, category, count):
        """
        Tests filtering by event category.
        """
        UserEvent.objects.all().delete()  # make sure that no user events exist
        info_events = EventFactory.create_batch(3, category=EventCategory.SUSHI)
        error_events = EventFactory.create_batch(5, category=EventCategory.TAGS)
        EventFactory.create_batch(7)  # these are unconnected events, just to make sure
        for e in info_events + error_events:
            e.assign_to_users([admin_user])

        response = admin_client.get(
            reverse("user-events-list"),
            {"category": category} if category else None,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == count
        assert len(data["results"]) == count
        if category:
            assert all(rec["category"] == category for rec in data["results"])

    @pytest.mark.parametrize("read", (True, False))
    def test_user_event_list_filtering_by_read(self, admin_client, admin_user, read):
        """
        Tests filtering by read status.
        """
        UserEvent.objects.all().delete()  # make sure that no user events exist
        events = EventFactory.create_batch(10)
        for idx, e in enumerate(events):
            e.assign_to_users([admin_user], read=(idx % 2 == 0))

        response = admin_client.get(
            reverse("user-events-list"),
            {"read": str(read).lower()},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 5
        assert len(data["results"]) == 5
        assert data["results"][0]["read"] is read

    @pytest.mark.parametrize(
        ["text", "count"],
        [("bar", 8), ("foo", 3), ("moo", 5), ("baz", 3), ("quix", 0), ("", 8)],
    )
    def test_user_events_list_search_filter(self, admin_client, admin_user, text, count):
        """
        Tests filtering by search query.
        """
        UserEvent.objects.all().delete()  # make sure that no user events exist
        events1 = EventFactory.create_batch(3, title="Foo bar baz", description="Whatever")
        events2 = EventFactory.create_batch(5, title="Bar bar bar", description="moo")
        EventFactory.create_batch(7)
        for e in events1 + events2:
            e.assign_to_users([admin_user])

        response = admin_client.get(
            reverse("user-events-list"),
            {"search": text},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == count
        assert len(data["results"]) == count
        assert all(
            text in rec["title"].lower() or text in rec["description"].lower()
            for rec in data["results"]
        )

    @pytest.mark.parametrize("desc", (True, False))
    @pytest.mark.parametrize("order_by", ("created", "title", "read"))
    def test_user_events_list_sorting(self, admin_client, admin_user, order_by, desc):
        """
        Tests sorting by different fields.
        """
        UserEvent.objects.all().delete()  # make sure that no user events exist
        events = EventFactory.create_batch(3)
        for idx, e in enumerate(events):
            e.assign_to_users([admin_user], read=(idx % 2 == 0))

        response = admin_client.get(
            reverse("user-events-list"),
            {"order_by": order_by, "desc": str(desc).lower()},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        assert len(data["results"]) == 3
        if desc:
            assert all(
                data["results"][i][order_by] >= data["results"][i + 1][order_by]
                for i in range(len(data["results"]) - 1)
            )
        else:
            assert all(
                data["results"][i][order_by] <= data["results"][i + 1][order_by]
                for i in range(len(data["results"]) - 1)
            )

    @pytest.mark.parametrize(
        ["page", "page_size", "count"],
        [
            (1, 5, 5),
            (2, 5, 5),
            (3, 5, 3),
            (1, 10, 10),
            (2, 10, 3),
            (1, 20, 13),
            (2, 20, 0),
        ],
    )
    def test_user_events_list_pagination(self, admin_client, admin_user, page, page_size, count):
        """
        Tests pagination.
        """
        UserEvent.objects.all().delete()  # make sure that no user events exist
        events = EventFactory.create_batch(13)
        for e in events:
            e.assign_to_users([admin_user])

        response = admin_client.get(
            reverse("user-events-list"), {"page": page, "page_size": page_size}
        )
        if count:
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 13
            assert len(data["results"]) == count
        else:
            assert response.status_code == 404, "page outside of range"

    @pytest.mark.parametrize(
        ["date", "filters", "counts", "last_exists"],
        [
            (
                "2023-01-03",
                {},
                (
                    8,
                    3,
                    {
                        "read": [
                            {"read": False, "count": 3},
                            {"read": True, "count": 5},
                        ],
                        "category": [
                            {"category": "overlap", "count": 4},
                            {"category": "sushi", "count": 4},
                        ],
                        "importance": [
                            {"importance": 10, "count": 5},
                            {"importance": 20, "count": 3},
                        ],
                    },
                ),
                True,
            ),
            (
                "2023-02-03",
                {},
                (
                    5,
                    0,
                    {
                        "read": [
                            {"read": True, "count": 5},
                        ],
                        "category": [
                            {"category": "overlap", "count": 2},
                            {"category": "sushi", "count": 3},
                        ],
                        "importance": [
                            {"importance": 10, "count": 3},
                            {"importance": 20, "count": 2},
                        ],
                    },
                ),
                True,
            ),
            (
                "2023-03-03",
                {},
                (0, 0, {"category": [], "importance": [], "read": []}),
                False,
            ),
            (
                "2023-01-03",
                {"read": True},
                (
                    8,
                    3,
                    {
                        "read": [
                            {"read": False, "count": 3},
                            {"read": True, "count": 5},
                        ],
                        "category": [
                            {"category": "overlap", "count": 2},
                            {"category": "sushi", "count": 3},
                        ],
                        "importance": [
                            {"importance": 10, "count": 3},
                            {"importance": 20, "count": 2},
                        ],
                    },
                ),
                True,
            ),
            (
                "2023-01-03",
                {"category": "sushi"},
                (
                    8,
                    3,
                    {
                        "read": [
                            {"read": False, "count": 1},
                            {"read": True, "count": 3},
                        ],
                        "category": [
                            {"category": "overlap", "count": 4},
                            {"category": "sushi", "count": 4},
                        ],
                        "importance": [
                            {"importance": 10, "count": 3},
                            {"importance": 20, "count": 1},
                        ],
                    },
                ),
                True,
            ),
            (
                "2023-01-03",
                {"importance": 20},
                (
                    8,
                    3,
                    {
                        "read": [
                            {"read": False, "count": 1},
                            {"read": True, "count": 2},
                        ],
                        "category": [
                            {"category": "overlap", "count": 2},
                            {"category": "sushi", "count": 1},
                        ],
                        "importance": [
                            {"importance": 10, "count": 5},
                            {"importance": 20, "count": 3},
                        ],
                    },
                ),
                True,
            ),
            (
                "2023-01-03",
                {"importance": 10, "category": "sushi", "read": True},
                (
                    8,
                    3,
                    {
                        "read": [
                            {"read": False, "count": 1},
                            {"read": True, "count": 2},
                        ],
                        "category": [
                            {"category": "overlap", "count": 1},
                            {"category": "sushi", "count": 2},
                        ],
                        "importance": [
                            {"importance": 10, "count": 2},
                            {"importance": 20, "count": 1},
                        ],
                    },
                ),
                True,
            ),
        ],
    )
    def test_stats_action(self, admin_client, admin_user, date, filters, counts, last_exists):
        """
        Tests that the stats action works as expected. It should only show events that are
        active = not expired.
        """
        with freeze_time("2023-01-01"):
            UserEvent.objects.all().delete()  # make sure that no user events exist

            UserEventFactory.create_batch(
                1,
                user=admin_user,
                event__expiration_date="2023-02-01",
                event__category=EventCategory.SUSHI,
                event__importance=EventImportance.NORMAL,
            )
            UserEventFactory.create_batch(
                1,
                user=admin_user,
                event__expiration_date="2023-02-01",
                event__category=EventCategory.OVERLAP,
                event__importance=EventImportance.NORMAL,
            )
            UserEventFactory.create_batch(
                1,
                user=admin_user,
                event__expiration_date="2023-02-01",
                event__category=EventCategory.OVERLAP,
                event__importance=EventImportance.HIGH,
            )

            UserEventFactory.create_batch(
                1,
                read=True,
                user=admin_user,
                event__expiration_date="2023-03-01",
                event__category=EventCategory.SUSHI,
                event__importance=EventImportance.HIGH,
            )
            UserEventFactory.create_batch(
                2,
                read=True,
                user=admin_user,
                event__expiration_date="2023-03-01",
                event__category=EventCategory.SUSHI,
                event__importance=EventImportance.NORMAL,
            )
            UserEventFactory.create_batch(
                1,
                read=True,
                user=admin_user,
                event__expiration_date="2023-03-01",
                event__category=EventCategory.OVERLAP,
                event__importance=EventImportance.NORMAL,
            )
            UserEventFactory.create_batch(
                1,
                read=True,
                user=admin_user,
                event__expiration_date="2023-03-01",
                event__category=EventCategory.OVERLAP,
                event__importance=EventImportance.HIGH,
            )

        with freeze_time(date):
            response = admin_client.get(reverse("user-events-stats"), filters)
            assert response.status_code == 200
            data = response.json()
            total, unread, filter_counts = counts
            assert data["total"] == total
            assert data["unread"] == unread
            assert data["newest_pk"] == (
                UserEvent.objects.order_by("event_id").last().event_id if last_exists else None
            )

            # Sort counts so the test can be fully deterministic
            data["counts"]["read"] = sorted(data["counts"]["read"], key=lambda x: x["read"])
            data["counts"]["importance"] = sorted(
                data["counts"]["importance"], key=lambda x: x["importance"]
            )
            data["counts"]["category"] = sorted(
                data["counts"]["category"], key=lambda x: x["category"]
            )
            assert data["counts"] == filter_counts

            if last_exists:
                assert isinstance(data["newest_event"], dict)

    @pytest.mark.parametrize(
        ["date", "count"], [("2023-01-03", 8), ("2023-02-03", 5), ("2023-03-03", 0)]
    )
    def test_user_events_list_with_lifetime(self, admin_client, admin_user, date, count):
        """
        Tests that the user events list endpoint works as expected when lifetime is set.
        """
        with freeze_time("2023-01-01"):
            UserEvent.objects.all().delete()  # make sure that no user events exist
            UserEventFactory.create_batch(3, user=admin_user, event__expiration_date="2023-02-01")
            UserEventFactory.create_batch(5, user=admin_user, event__expiration_date="2023-03-01")
        with freeze_time(date):
            response = admin_client.get(reverse("user-events-list"))
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == count
            assert len(data["results"]) == count


@pytest.mark.django_db
class TestUserEventExtraActions:
    @pytest.mark.parametrize(
        ["read_before", "read_after", "read_date_is_set"],
        [
            (True, True, False),
            (True, False, True),
            (False, True, True),
            (False, False, False),
        ],
    )
    def test_mark_read(self, admin_client, admin_user, read_before, read_after, read_date_is_set):
        """
        Tests that the mark read endpoint works as expected.
        """
        event = EventFactory.create()
        event.assign_to_users([admin_user], read=read_before)
        assert event.userevent_set.get(user=admin_user).first_read_date is None
        response = admin_client.post(
            reverse("user-events-mark-read", kwargs={"pk": event.pk}),
            data={"read": read_after},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["read"] is read_after
        assert event.userevent_set.get(user=admin_user).read is read_after
        assert (
            event.userevent_set.get(user=admin_user).first_read_date is not None
        ) == read_date_is_set

    def test_mark_read_multi(self, admin_client, admin_user):
        """
        Tests that the mark read endpoint works as expected for multiple events.
        """
        UserEvent.objects.all().delete()  # make sure that no user events exist
        events = EventFactory.create_batch(10)
        for idx, e in enumerate(events):
            e.assign_to_users([admin_user], read=(idx % 2 == 0))
        response = admin_client.post(
            reverse("user-events-mark-read-many"),
            data={"event_ids": [e.pk for e in events], "read": True},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["updated"] == 5
        assert data["skipped"] == 5
        assert all(e.userevent_set.get(user=admin_user).read for e in events)
        # try reversing a few
        response = admin_client.post(
            reverse("user-events-mark-read-many"),
            data={"event_ids": [e.pk for e in events[:3]], "read": False},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["updated"] == 3
        assert data["skipped"] == 0
        assert all(not e.userevent_set.get(user=admin_user).read for e in events[:3])


@pytest.mark.django_db
class TestUserPreferencesAPI:
    def test_get_user_preferences_defaults(self, admin_client):
        """
        Tests that the user preferences endpoint works as expected when no preferences are set.
        """
        response = admin_client.get(reverse("user-event-preferences-list"))
        assert response.status_code == 200
        data = response.json()
        for category in EventCategory.values:
            assert category in data
            assert isinstance(data[category], dict)
            for importance in EventImportance.values:
                # importance is converted from int to string during serialization
                # because JSON keys can only be strings
                importance_str = str(importance)
                assert importance_str in data[category]
                assert data[category][importance_str] == HandlingMethod.default()

    def test_get_user_preferences_some_settings(self, admin_client, admin_user):
        """
        Tests that the user preferences endpoint works as expected when no preferences are set.
        """
        UserEventCategoryHandling.objects.create(
            user=admin_user,
            category=EventCategory.SUSHI,
            importance=EventImportance.NORMAL,
            handling_method=HandlingMethod.EMAIL,
        )
        UserEventCategoryHandling.objects.create(
            user=admin_user,
            category=EventCategory.SUSHI,
            importance=EventImportance.HIGH,
            handling_method=HandlingMethod.IGNORE,
        )
        response = admin_client.get(reverse("user-event-preferences-list"))
        assert response.status_code == 200
        data = response.json()
        for category in EventCategory.values:
            # importance is converted from int to string during serialization
            # because JSON keys can only be strings
            assert category in data
            assert isinstance(data[category], dict)
            if category == EventCategory.SUSHI:
                # sushi was explicitly setup
                assert data[category][str(EventImportance.NORMAL)] == HandlingMethod.EMAIL
                assert data[category][str(EventImportance.HIGH)] == HandlingMethod.IGNORE
            else:
                for importance in EventImportance.values:
                    assert str(importance) in data[category]
                    assert data[category][str(importance)] == HandlingMethod.default()

    def test_set_user_preferences(self, admin_client):
        """
        Tests that the user preferences endpoint works as expected when no preferences are set.
        """
        response = admin_client.post(
            reverse("user-event-preferences-list"),
            data={
                EventCategory.SUSHI: {
                    str(EventImportance.NORMAL): HandlingMethod.IGNORE,
                    str(EventImportance.HIGH): HandlingMethod.EMAIL,
                },
                EventCategory.TAGS: {
                    str(EventImportance.NORMAL): HandlingMethod.EMAIL,
                    str(EventImportance.HIGH): HandlingMethod.IGNORE,
                },
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data[EventCategory.SUSHI][str(EventImportance.NORMAL)] == HandlingMethod.IGNORE
        assert data[EventCategory.SUSHI][str(EventImportance.HIGH)] == HandlingMethod.EMAIL
        assert data[EventCategory.TAGS][str(EventImportance.NORMAL)] == HandlingMethod.EMAIL
        assert data[EventCategory.TAGS][str(EventImportance.HIGH)] == HandlingMethod.IGNORE
        assert data[EventCategory.OVERLAP][str(EventImportance.NORMAL)] == HandlingMethod.default()
        assert data[EventCategory.OVERLAP][str(EventImportance.HIGH)] == HandlingMethod.default()
        # change one of the already set preferences to check that it's updated
        response = admin_client.post(
            reverse("user-event-preferences-list"),
            data={EventCategory.SUSHI: {str(EventImportance.NORMAL): HandlingMethod.EMAIL}},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data[EventCategory.SUSHI][str(EventImportance.NORMAL)] == HandlingMethod.EMAIL
