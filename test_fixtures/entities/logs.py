from datetime import date
from random import randint

import factory
import faker
from dateutil.relativedelta import relativedelta
from django.conf import settings
from test_fixtures.entities.organizations import OrganizationFactory
from test_fixtures.entities.platforms import PlatformFactory
from test_fixtures.entities.report_types import ReportTypeFactory

from logs.logic.clickhouse import sync_import_batch_with_clickhouse
from logs.models import AccessLog, ImportBatch, ManualDataUpload, MduState, Metric

fake = faker.Faker()

DATA_FILE = b"""\
Title,Metric,Publisher,Success,Jan 2020, Feb 2020, Mar 2020
A,views,Pub1,Success,0,1,2
A,views,Pub1,Denied,1,0,0
B,views,Pub1,Success,0,0,0
B,views,Pub1,Denied,1,1,1
C,views,Pub2,Success,3,3,3
C,views,Pub2,Denied,4,4,4"""


class MetricFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Metric

    short_name = factory.Faker('name')
    name = factory.Faker('name')


class ImportBatchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ImportBatch


class AccessLogFactory(factory.django.DjangoModelFactory):
    import_batch = factory.SubFactory(ImportBatchFactory)
    value = factory.LazyFunction(lambda: randint(1, 5000))

    date = factory.SelfAttribute('import_batch.date')
    organization = factory.SelfAttribute('import_batch.organization')
    report_type = factory.SelfAttribute('import_batch.report_type')
    platform = factory.SelfAttribute('import_batch.platform')

    class Meta:
        model = AccessLog


class ImportBatchFullFactory(factory.django.DjangoModelFactory):
    """
    Factory to create import batch with the report type, organization, platform, metrics and
    data.
    """

    class Meta:
        model = ImportBatch

    organization = factory.SubFactory(OrganizationFactory)
    platform = factory.SubFactory(PlatformFactory)
    report_type = factory.SubFactory(ReportTypeFactory)
    date = factory.Faker('date_this_century')

    @factory.post_generation
    def create_accesslogs(obj, create, extracted, **kwargs):  # noqa - obj name is ok here
        if not create:
            return
        m1 = MetricFactory.create()
        m2 = MetricFactory.create()
        attrs = {
            'import_batch': obj,
            'organization': obj.organization,
            'platform': obj.platform,
            'report_type': obj.report_type,
            'date': obj.date,
        }
        als1 = [AccessLog(value=fake.random_int(), metric=m1, **attrs) for _i in range(10)]
        als2 = [AccessLog(value=fake.random_int(), metric=m2, **attrs) for _i in range(10)]
        AccessLog.objects.bulk_create(als1 + als2)
        if settings.CLICKHOUSE_SYNC_ACTIVE:
            sync_import_batch_with_clickhouse(obj)


class ManualDataUploadFullFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ManualDataUpload

    organization = factory.SubFactory(OrganizationFactory)
    platform = factory.SubFactory(PlatformFactory)
    report_type = factory.SubFactory(ReportTypeFactory)

    state = MduState.IMPORTED
    when_processed = factory.LazyAttribute(
        lambda o: fake.date_time_this_year() if o.state == MduState.IMPORTED else None
    )
    data_file = factory.django.FileField(data=DATA_FILE)

    @factory.post_generation
    def create_import_batches(obj, create, extracted, **kwargs):  # noqa - obj name is ok here
        if not create:
            return

        if obj.is_processed:
            ib = ImportBatchFullFactory.create(
                organization=obj.organization, platform=obj.platform, report_type=obj.report_type
            )
            obj.import_batches.set([ib])


class ManualDataUploadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ManualDataUpload

    organization = factory.SubFactory(OrganizationFactory)
    platform = factory.SubFactory(PlatformFactory)
    report_type = factory.SubFactory(ReportTypeFactory)

    state = MduState.IMPORTED
    when_processed = factory.LazyAttribute(
        lambda o: fake.date_time_this_year() if o.state == MduState.IMPORTED else None
    )
    data_file = factory.django.FileField(data=DATA_FILE)

    @factory.post_generation
    def import_batches(self, create, extracted, **kwargs):  # noqa - obj name is ok here
        if not create:
            return
        if extracted:
            for batch in extracted:
                self.import_batches.add(batch)
