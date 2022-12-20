import factory
from factory.fuzzy import FuzzyChoice
from faker import Faker
from sushi.models import COUNTER_VERSIONS, SushiCredentials

from .organizations import OrganizationFactory
from .platforms import PlatformFactory

fake = Faker()


class CredentialsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SushiCredentials

    title = factory.Faker('name')
    organization = factory.SubFactory(OrganizationFactory)
    platform = factory.SubFactory(PlatformFactory)
    url = factory.Faker('url')
    counter_version = FuzzyChoice(COUNTER_VERSIONS, getter=lambda e: e[0])
