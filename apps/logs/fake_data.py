from datetime import date
from random import randint

import factory
import faker
from celus_nigiri.counter5 import CounterRecord
from core.fake_data import UserFactory
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.utils import timezone
from organizations.fake_data import OrganizationFactory
from publications.fake_data import PlatformFactory, TitleFactory
from publications.models import PlatformTitle

from logs.logic.clickhouse import sync_import_batch_with_clickhouse
from logs.models import (
    AccessLog,
    Dimension,
    DimensionText,
    ImportBatch,
    InterestGroup,
    ManualDataUpload,
    MduState,
    Metric,
    ReportType,
    ReportTypeToDimension,
)

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

    short_name = factory.Faker("name")
    name = factory.Faker("name")


class ReportTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ReportType
        django_get_or_create = ("short_name",)

    name = "Counter 5 - Title report"
    short_name = "TR"

    @factory.post_generation
    def dimensions(obj, create, extracted: [str], **kwargs):  # noqa - obj name is ok here
        if not create:
            return

        if extracted:
            for i, d in enumerate(extracted):
                dim, _created = Dimension.objects.get_or_create(short_name=d, defaults={"name": d})
                ReportTypeToDimension.objects.create(report_type=obj, dimension=dim, position=i)


class ImportBatchFactory(factory.django.DjangoModelFactory):
    """
    Factory to create import batch with the report type, organization, platform, metrics,
    but without data
    """

    class Meta:
        model = ImportBatch

    organization = factory.SubFactory(OrganizationFactory)
    platform = factory.SubFactory(PlatformFactory)
    report_type = factory.SubFactory(ReportTypeFactory)
    date = factory.Faker("date_this_century")


class AccessLogFactory(factory.django.DjangoModelFactory):
    import_batch = factory.SubFactory(ImportBatchFactory)
    value = factory.LazyFunction(lambda: randint(1, 5000))

    date = factory.SelfAttribute("import_batch.date")
    organization = factory.SelfAttribute("import_batch.organization")
    report_type = factory.SelfAttribute("import_batch.report_type")
    platform = factory.SelfAttribute("import_batch.platform")

    class Meta:
        model = AccessLog


class ImportBatchFullFactory(ImportBatchFactory):
    """
    Factory to create import batch with the report type, organization, platform, metrics and
    data.
    """

    @factory.post_generation
    def create_accesslogs(obj, create, extracted, **kwargs):  # noqa - obj name is ok here
        if not create:
            return

        if not (metrics := kwargs.pop("metrics", None)):
            metrics = MetricFactory.create_batch(2)
        if not (titles := kwargs.pop("titles", None)):
            titles = TitleFactory.create_batch(10)
        value = kwargs.pop("value", None)  # all access logs will have the same value if provided

        attrs = {
            "import_batch": obj,
            "organization": obj.organization,
            "platform": obj.platform,
            "report_type": obj.report_type,
            "date": obj.date,
            **kwargs,
        }
        als = []
        for m in metrics:
            als += [
                AccessLog(value=value or fake.random_int(), metric=m, target=t, **attrs)
                for t in titles
            ]
        AccessLog.objects.bulk_create(als)

        PlatformTitle.objects.bulk_create(
            [
                PlatformTitle(
                    platform=obj.platform, organization=obj.organization, date=obj.date, title=t
                )
                for t in titles
            ],
            ignore_conflicts=True,
        )

        if settings.CLICKHOUSE_SYNC_ACTIVE:
            sync_import_batch_with_clickhouse(obj)


class ManualDataUploadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ManualDataUpload

    organization = factory.SubFactory(OrganizationFactory)
    platform = factory.SubFactory(PlatformFactory)
    report_type = factory.SubFactory(ReportTypeFactory)
    user = factory.SubFactory(UserFactory)

    state = MduState.IMPORTED
    when_processed = factory.LazyAttribute(
        lambda o: fake.date_time_this_year(tzinfo=timezone.get_default_timezone())
        if o.state == MduState.IMPORTED
        else None
    )
    data_file = factory.django.FileField(data=DATA_FILE)
    file_size = factory.LazyAttribute(
        lambda x: x.data_file.size if hasattr(x.data_file, "size") else len(x.data_file)
    )
    checksum = factory.LazyAttribute(
        lambda x: ManualDataUpload.checksum_fileobj(x.data_file)[0]
        if hasattr(x.data_file, "seek")
        else "foobar"
    )

    @factory.post_generation
    def import_batches(self, create, extracted, **kwargs):  # noqa - obj name is ok here
        if not create:
            return
        if extracted:
            for batch in extracted:
                self.import_batches.add(batch)


class ManualDataUploadFullFactory(ManualDataUploadFactory):
    @factory.post_generation
    def import_batches(obj, create, extracted, **kwargs):  # noqa - obj name is ok here
        if not create:
            return

        if obj.is_processed:
            ib = ImportBatchFullFactory.create(
                organization=obj.organization, platform=obj.platform, report_type=obj.report_type
            )
            obj.import_batches.set([ib])


class InterestGroupFactory(factory.django.DjangoModelFactory):
    short_name = factory.Faker("slug")
    position = 1

    class Meta:
        model = InterestGroup


# Fake counter records from nigiri
def create_title_ids():
    return {"Print_ISSN": "1234-5678", "ISBN": "9780471397120"}


def create_item_ids():
    return {"Print_ISSN": "1234-1234", "DOI": "10.1111/aaa.1234"}


def create_dim_data(obj):
    return []


class CounterRecordFactory(factory.Factory):
    class Meta:
        model = CounterRecord

    start = factory.LazyFunction(lambda: date(randint(2010, 2021), randint(1, 12), 1))
    end = factory.LazyAttribute(lambda x: x.start + relativedelta(months=1) - relativedelta(days=1))
    metric = factory.LazyFunction(lambda: f"Metric {fake.pyint()}")
    value = factory.Faker("random_int")
    dimension_data = factory.LazyAttribute(create_dim_data)
    title = factory.Faker("sentence")
    title_ids = factory.LazyFunction(create_title_ids)
    item = factory.Faker("sentence")
    item_ids = factory.LazyFunction(create_item_ids)


class DimensionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Dimension

    short_name = factory.Faker("slug")
    name = factory.Faker("sentence")


class DimensionTextFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DimensionText

    dimension = factory.SubFactory(DimensionFactory)
