import factory
from core.fake_data import UserFactory
from django_celus_registry import models as dcr_models
from events.fake_data import EventFactory
from faker import Faker

from counter_registry.models import (
    CounterRegistryProfile,
    NotificationEvent,
    Platform,
    PlatformExtras,
    Report,
    SushiService,
)

fake = Faker()


class PlatformFactory(factory.django.DjangoModelFactory):
    id = factory.Faker("uuid4")
    name = factory.Faker("sentence")

    class Meta:
        model = Platform
        django_get_or_create = ("id",)


class PlatformExtrasFactory(factory.django.DjangoModelFactory):
    knowledgebase = {}
    notes = factory.Faker("sentence")
    platform = factory.SubFactory(PlatformFactory)

    class Meta:
        model = PlatformExtras
        django_get_or_create = ("platform",)


class ReportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Report


class SushiServiceFactory(factory.django.DjangoModelFactory):
    id = factory.Faker("uuid4")
    platform = factory.SubFactory(PlatformFactory)
    counter_release = 5
    url = factory.Faker("url")

    class Meta:
        model = SushiService
        django_get_or_create = ("id",)


class NotificationFactory(factory.django.DjangoModelFactory):
    id = factory.Faker("uuid4")
    sushi_service = factory.SubFactory(SushiServiceFactory)
    last_modified = factory.Faker("date_time")

    class Meta:
        model = dcr_models.Notification


class NotificationEventFactory(factory.django.DjangoModelFactory):
    notification = factory.SubFactory(NotificationFactory)
    event = factory.SubFactory(EventFactory)

    class Meta:
        model = NotificationEvent


class CounterRegistryProfileFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = CounterRegistryProfile
