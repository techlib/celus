import pytest
from core.fake_data import UserFactory

from events.models import UserEvent


@pytest.mark.django_db
class TestSignals:
    @pytest.mark.parametrize("create_welcome_events", [True, False])
    def test_welcome_event(self, settings, create_welcome_events):
        """
        Test that the welcome event is created for new users.
        """
        settings.CREATE_USER_WELCOME_EVENTS = create_welcome_events
        u = UserFactory.create()
        if create_welcome_events:
            assert UserEvent.objects.count() == 1
            assert "welcome" in UserEvent.objects.filter(user=u).first().event.title.lower()
        else:
            assert UserEvent.objects.count() == 0
