import factory
from charts.models import ChartDefinition, ReportDataView

from test_fixtures.entities.report_types import ReportTypeFactory


class ChartDefinitionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ChartDefinition

    name = factory.Faker('name')
    primary_implicit_dimension = 'date'
    secondary_implicit_dimension = 'metric'
    is_generic = False


class ReportDataViewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ReportDataView

    base_report_type = factory.SubFactory(ReportTypeFactory)
    name = factory.LazyAttribute(lambda o: o.base_report_type.name)
