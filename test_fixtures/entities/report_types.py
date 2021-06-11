import factory

from logs.models import ReportType


class ReportTypeFactory(factory.DjangoModelFactory):
    class Meta:
        model = ReportType
        django_get_or_create = ('short_name',)

    name = 'Counter 5 - Title report'
    short_name = 'TR'
