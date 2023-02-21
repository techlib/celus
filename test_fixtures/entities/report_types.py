import factory
from logs.models import Dimension, ReportType, ReportTypeToDimension


class ReportTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ReportType
        django_get_or_create = ('short_name',)

    name = 'Counter 5 - Title report'
    short_name = 'TR'

    @factory.post_generation
    def dimensions(obj, create, extracted: [str], **kwargs):  # noqa - obj name is ok here
        if not create:
            return

        if extracted:
            for i, d in enumerate(extracted):
                dim, _created = Dimension.objects.get_or_create(short_name=d, defaults={"name": d})
                ReportTypeToDimension.objects.create(report_type=obj, dimension=dim, position=i)
