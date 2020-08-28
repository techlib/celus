import factory

from sushi.models import CounterReportType

from .report_types import ReportTypeFactory


class CounterReportTypeFactory(factory.DjangoModelFactory):
    class Meta:
        model = CounterReportType

    code = 'TR'
    counter_version = 5
    report_type = factory.SubFactory(ReportTypeFactory)
    active = True
