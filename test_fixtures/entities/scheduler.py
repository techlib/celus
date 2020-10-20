from datetime import date

import factory
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from scheduler.models import FetchIntention, Harvest, Scheduler
from .credentials import CredentialsFactory
from .counter_report_types import CounterReportTypeFactory
from .users import UserFactory


class HarvestFactory(factory.DjangoModelFactory):
    last_updated_by = factory.SubFactory(UserFactory)

    class Meta:
        model = Harvest


class SchedulerFactory(factory.DjangoModelFactory):
    url = factory.Faker('url')

    class Meta:
        model = Scheduler


class FetchIntentionFactory(factory.DjangoModelFactory):
    harvest = factory.SubFactory(HarvestFactory)
    not_before = timezone.now()
    credentials = factory.SubFactory(CredentialsFactory)
    counter_report = factory.SubFactory(CounterReportTypeFactory)
    start_date = date(2020, 1, 1)
    end_date = factory.LazyAttribute(
        lambda x: x.start_date + relativedelta(months=1) - relativedelta(days=1)
    )

    class Meta:
        model = FetchIntention
