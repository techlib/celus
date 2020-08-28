import factory

from logs.models import ReportType


class ReportTypeFactory(factory.DjangoModelFactory):
    class Meta:
        model = ReportType

    name = 'Counter 5 - Title report'
    short_name = 'TR'
