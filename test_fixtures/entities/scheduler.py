from datetime import date

import factory
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from scheduler.models import Automatic, FetchIntention, FetchIntentionQueue, Harvest, Scheduler
from .credentials import CredentialsFactory
from .counter_report_types import CounterReportTypeFactory
from .organizations import OrganizationFactory
from .users import UserFactory
from .fetchattempts import FetchAttemptFactory


class HarvestFactory(factory.django.DjangoModelFactory):
    last_updated_by = factory.SubFactory(UserFactory)

    class Meta:
        model = Harvest

    @factory.post_generation
    def intentions(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for intention in extracted:
                if intention.attempt:
                    intention.attempt.save()
                intention.harvest = self
                intention.save()
                if not intention.queue:
                    intention.queue = FetchIntentionQueueFactory(
                        id=intention.pk, start=intention, end=intention
                    )


class SchedulerFactory(factory.django.DjangoModelFactory):
    url = factory.Faker('url')

    class Meta:
        model = Scheduler


class FetchIntentionQueueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FetchIntentionQueue
        django_get_or_create = ('id',)


class FetchIntentionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FetchIntention

    harvest = factory.SubFactory(HarvestFactory)
    attempt = factory.SubFactory(
        FetchAttemptFactory,
        counter_report=factory.SelfAttribute('..counter_report'),
        credentials=factory.SelfAttribute('..credentials'),
        start_date=factory.SelfAttribute('..start_date'),
        end_date=factory.SelfAttribute('..end_date'),
    )
    not_before = timezone.now()
    credentials = factory.SubFactory(CredentialsFactory)
    counter_report = factory.SubFactory(CounterReportTypeFactory)
    start_date = date(2020, 1, 1)
    end_date = factory.LazyAttribute(
        lambda x: x.start_date + relativedelta(months=1) - relativedelta(days=1)
    )

    @factory.post_generation
    def queue(obj, create, extracted, **kwargs):
        if extracted:
            obj.queue = extracted
        if obj.pk and not obj.queue:
            if create:
                obj.queue = FetchIntentionQueueFactory(id=obj.pk, start=obj, end=obj)
            else:
                obj.queue = FetchIntentionQueueFactory.build(id=obj.pk, start=obj, end=obj)

        if obj.queue and obj.pk:
            obj.queue.end = obj
            obj.queue.save()


class AutomaticFactory(factory.django.DjangoModelFactory):
    month = date(2020, 1, 1)
    organization = factory.SubFactory(OrganizationFactory)
    harvest = factory.SubFactory(HarvestFactory)

    class Meta:
        model = Automatic
