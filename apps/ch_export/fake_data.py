import factory
from organizations.fake_data import OrganizationFactory

from ch_export.models import AccessLogExport


class AccessLogExportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AccessLogExport

    organization = factory.SubFactory(OrganizationFactory)
    settings = factory.LazyFunction(lambda: {})
    enabled = True
