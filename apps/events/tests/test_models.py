from unittest.mock import patch

import pytest
from core.fake_data import UserFactory
from core.models import User

from events.fake_data import EventFactory, UserEventFactory
from events.models import (
    Event,
    EventCategory,
    EventImportance,
    HandlingMethod,
    UserEvent,
    UserEventCategoryHandling,
)


@pytest.mark.django_db
class TestEvent:
    def test_assign_event_to_users(self, django_assert_max_num_queries):
        """
        Tests assigning an event to a subset of users.
        """

        UserFactory.create_batch(10)
        event = EventFactory.create()
        with django_assert_max_num_queries(3):
            event.assign_to_users(User.objects.all()[:5])
        assert UserEvent.objects.count() == 5

    def test_assign_event_to_users_handling(self):
        """
        Test that the `.handling` attribute of created `UserEvents` matches the user's preferred
        handling method as specified using the `UserEventCategoryHandling` model.
        """
        u1, u2, u3 = UserFactory.create_batch(3)
        event = EventFactory.create()
        UserEventCategoryHandling.objects.create(
            user=u1,
            category=event.category,
            importance=event.importance,
            handling_method=HandlingMethod.EMAIL,
        )
        UserEventCategoryHandling.objects.create(
            user=u2,
            category=event.category,
            importance=event.importance,
            handling_method=HandlingMethod.NOTIFY_IN_APP,
        )
        # user u3 has no explicit handling method set, so it should default to default()
        event.assign_to_users([u1, u2, u3])
        assert UserEvent.objects.count() == 3
        assert UserEvent.objects.filter(user=u1).first().handling == HandlingMethod.EMAIL
        assert UserEvent.objects.filter(user=u2).first().handling == HandlingMethod.NOTIFY_IN_APP
        assert UserEvent.objects.filter(user=u3).first().handling == HandlingMethod.default()

    def test_assign_event_to_user_with_ignored(self):
        """
        Test that when handling is set to `ignore` no link between the user and the event is
        created.
        """
        u1, u2 = UserFactory.create_batch(2)
        event = EventFactory.create()
        UserEventCategoryHandling.objects.create(
            user=u1,
            category=event.category,
            importance=event.importance,
            handling_method=HandlingMethod.IGNORE,
        )
        event.assign_to_users([u1, u2])
        assert UserEvent.objects.count() == 1
        assert UserEvent.objects.filter(user=u1).first() is None
        assert UserEvent.objects.filter(user=u2).first() is not None

    @pytest.mark.parametrize("first_user_email", (True, False))
    def test_create_for_users(self, first_user_email):
        """
        Test that the convenience class method `create_for_users` works as expected.
        """
        u1, u2, u3 = UserFactory.create_batch(3)
        UserEventCategoryHandling.objects.create(
            user=u1,
            category=EventCategory.SUSHI,
            importance=EventImportance.NORMAL,
            handling_method=HandlingMethod.EMAIL
            if first_user_email
            else HandlingMethod.NOTIFY_IN_APP,
        )
        UserEventCategoryHandling.objects.create(
            user=u2,
            category=EventCategory.SUSHI,
            importance=EventImportance.NORMAL,
            handling_method=HandlingMethod.NOTIFY_IN_APP,
        )
        # user u3 has no explicit handling method set, so it should default to default()
        with patch("events.tasks.send_unsent_event_emails_task") as mock_send_email:
            Event.create_for_users(
                [u1, u2, u3],
                category=EventCategory.SUSHI,
                importance=EventImportance.NORMAL,
                title="test",
                description="test",
            )
            if first_user_email:
                assert mock_send_email.delay.call_count == 1, "one user has email handling method"
            else:
                assert mock_send_email.delay.call_count == 0, "no user has email handling method"
        assert UserEvent.objects.count() == 3


@pytest.mark.django_db
class TestUserEvent:
    def test_send_emails(self, mailoutbox):
        """
        Tests that the custom manager method send_emails works as expected.
        """
        UserEventFactory.create_batch(10, handling=HandlingMethod.EMAIL)
        assert UserEvent.objects.send_emails() == 10
        assert len(mailoutbox) == 10
