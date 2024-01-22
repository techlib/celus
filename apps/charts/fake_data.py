import factory
from logs.fake_data import ReportTypeFactory

from charts.models import ChartDefinition, ReportDataView


class ChartDefinitionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ChartDefinition

    name = factory.Faker("name")
    primary_implicit_dimension = "date"
    secondary_implicit_dimension = "metric"
    is_generic = False


class ReportDataViewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ReportDataView

    base_report_type = factory.SubFactory(ReportTypeFactory)
    name = factory.LazyAttribute(lambda o: o.base_report_type.name)
