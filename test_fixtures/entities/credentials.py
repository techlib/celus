import factory
from core.models import UL_ORG_ADMIN
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
    lock_level = UL_ORG_ADMIN
    requestor_id = factory.Faker('password')
    customer_id = factory.Faker('password')
    http_username = factory.LazyAttribute(
        lambda obj: fake.simple_profile()["username"] if obj.counter_version == 4 else ''
    )
    http_password = factory.LazyAttribute(
        lambda obj: fake.password() if obj.counter_version == 4 else ''
    )
    api_key = factory.LazyAttribute(lambda obj: fake.uuid4() if obj.counter_version == 5 else '')
