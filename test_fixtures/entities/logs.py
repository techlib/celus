import factory
import faker
from django.conf import settings

from logs.logic.clickhouse import sync_import_batch_with_clickhouse
from logs.models import ImportBatch, Metric, AccessLog, ManualDataUpload
from test_fixtures.entities.organizations import OrganizationFactory
from test_fixtures.entities.platforms import PlatformFactory
from test_fixtures.entities.report_types import ReportTypeFactory


fake = faker.Faker()


class MetricFactory(factory.DjangoModelFactory):
    class Meta:
        model = Metric

    short_name = factory.Faker('name')
    name = factory.Faker('name')


class ImportBatchFactory(factory.DjangoModelFactory):
    class Meta:
        model = ImportBatch


class ImportBatchFullFactory(factory.DjangoModelFactory):
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


class ManualDataUploadFullFactory(factory.DjangoModelFactory):
    class Meta:
        model = ManualDataUpload

    organization = factory.SubFactory(OrganizationFactory)
    platform = factory.SubFactory(PlatformFactory)
    report_type = factory.SubFactory(ReportTypeFactory)

    is_processed = True
    when_processed = factory.LazyAttribute(
        lambda o: fake.date_time_this_year() if o.is_processed else None
    )

    @factory.post_generation
    def create_import_batches(obj, create, extracted, **kwargs):  # noqa - obj name is ok here
        if not create:
            return

        if obj.is_processed:
            ib = ImportBatchFullFactory.create(
                organization=obj.organization, platform=obj.platform, report_type=obj.report_type
            )
            obj.import_batches.set([ib])
