import factory
from core.models import UL_ORG_ADMIN
from factory.fuzzy import FuzzyChoice
from faker import Faker
from scheduler import signals as scheduler_signals
from sushi.models import COUNTER_VERSIONS, CounterReportsToCredentials, SushiCredentials

from .counter_report_types import CounterReportTypeFactory
from .organizations import OrganizationFactory
from .platforms import PlatformFactory

fake = Faker()


# post_generation hooks call a second save() on the model which in our case triggers
# the post_save signal again which messes up planned harvesting. Therefor we mute the signal here
@factory.django.mute_signals(scheduler_signals.post_save)
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

    @factory.post_generation
    def report_types(obj, create, extracted, **kwargs):  # noqa - obj name is ok here
        if not create:
            return
        if extracted:
            for report_type_name in extracted:
                rt = CounterReportTypeFactory(code=report_type_name)
                CounterReportsToCredentials.objects.get_or_create(
                    counter_report=rt, credentials=obj
                )
