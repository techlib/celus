import factory
from counter_registry.models import Platform, PlatformExtras, Report, SushiService
from faker import Faker

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

    class Meta:
        model = SushiService
        django_get_or_create = ("id",)
