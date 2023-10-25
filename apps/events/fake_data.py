import factory
from factory.fuzzy import FuzzyChoice

from events.models import Event, EventCategory, EventImportance, HandlingMethod, UserEvent


class EventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Event

    title = factory.Faker("sentence", nb_words=5)
    description = factory.Faker("text")
    expiration_date = None
    importance = FuzzyChoice(EventImportance.values)
    category = FuzzyChoice(EventCategory.values)
    platform = None


class UserEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserEvent

    user = factory.SubFactory("core.fake_data.UserFactory")
    event = factory.SubFactory(EventFactory)
    handling = FuzzyChoice(HandlingMethod.values)
    read = False
    email_sent_date = None
