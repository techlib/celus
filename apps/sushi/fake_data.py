from datetime import date
from random import randint

import factory
from core.models import UL_ORG_ADMIN
from dateutil.relativedelta import relativedelta
from factory.fuzzy import FuzzyChoice
from faker import Faker
from logs.fake_data import ReportTypeFactory
from organizations.fake_data import OrganizationFactory
from publications.fake_data import PlatformFactory
from scheduler import signals as scheduler_signals

from sushi.models import (
    COUNTER_VERSIONS,
    AttemptStatus,
    CounterReportsToCredentials,
    CounterReportType,
    SushiCredentials,
    SushiFetchAttempt,
)

fake = Faker()


class CounterReportTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CounterReportType
        django_get_or_create = ("code",)

    code = "TR"
    counter_version = 5
    report_type = factory.SubFactory(ReportTypeFactory, short_name=factory.SelfAttribute("..code"))
    active = True


# post_generation hooks call a second save() on the model which in our case triggers
# the post_save signal again which messes up planned harvesting. Therefor we mute the signal here
@factory.django.mute_signals(scheduler_signals.post_save)
class CredentialsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SushiCredentials

    title = factory.Faker("name")
    organization = factory.SubFactory(OrganizationFactory)
    platform = factory.SubFactory(PlatformFactory)
    url = factory.Faker("url")
    counter_version = FuzzyChoice(COUNTER_VERSIONS, getter=lambda e: e[0])
    lock_level = UL_ORG_ADMIN
    requestor_id = factory.Faker("password")
    customer_id = factory.Faker("password")
    http_username = factory.LazyAttribute(
        lambda obj: fake.simple_profile()["username"] if obj.counter_version == 4 else ""
    )
    http_password = factory.LazyAttribute(
        lambda obj: fake.password() if obj.counter_version == 4 else ""
    )
    api_key = factory.LazyAttribute(lambda obj: fake.uuid4() if obj.counter_version == 5 else "")

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


class FetchAttemptFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SushiFetchAttempt

    credentials = factory.SubFactory(CredentialsFactory)
    counter_report = factory.SubFactory(CounterReportTypeFactory)
    credentials_version_hash = factory.LazyAttribute(lambda x: x.credentials.version_hash)

    start_date = factory.LazyFunction(lambda: date(randint(2010, 2021), randint(1, 12), 1))
    end_date = factory.LazyAttribute(
        lambda x: x.start_date + relativedelta(months=1) - relativedelta(days=1)
    )
    import_batch = None
    status = AttemptStatus.SUCCESS
    data_file = factory.django.FileField()
    file_size = factory.LazyAttribute(
        lambda x: x.data_file.size if hasattr(x.data_file, "size") else 0
    )
    checksum = factory.LazyAttribute(
        lambda x: SushiFetchAttempt.checksum_fileobj(x.data_file)[0]
        if hasattr(x.data_file, "seek")
        else "foobar"
    )
