import factory
import faker

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
            'date': '2020-01-01',
        }
        als1 = [AccessLog(value=fake.random_int(), metric=m1, **attrs) for _i in range(10)]
        als2 = [AccessLog(value=fake.random_int(), metric=m2, **attrs) for _i in range(10)]
        AccessLog.objects.bulk_create(als1 + als2)


class ManualDataUploadFullFactory(factory.DjangoModelFactory):
    class Meta:
        model = ManualDataUpload

    organization = factory.SubFactory(OrganizationFactory)
    platform = factory.SubFactory(PlatformFactory)
    report_type = factory.SubFactory(ReportTypeFactory)

    import_batch = factory.SubFactory(
        ImportBatchFullFactory,
        organization=factory.SelfAttribute('..organization'),
        platform=factory.SelfAttribute('..platform'),
        report_type=factory.SelfAttribute('..report_type'),
    )
    is_processed = True
    when_processed = factory.LazyAttribute(
        lambda o: fake.date_time_this_year() if o.is_processed else None
    )
