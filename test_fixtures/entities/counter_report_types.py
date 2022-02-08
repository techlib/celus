import factory

from sushi.models import CounterReportType

from .report_types import ReportTypeFactory


class CounterReportTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CounterReportType
        django_get_or_create = ('code',)

    code = 'TR'
    counter_version = 5
    report_type = factory.SubFactory(ReportTypeFactory)
    active = True
