import factory
from nibbler.models import ParserDefinition


class ParserDefinitionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ParserDefinition
        django_get_or_create = ('id',)

    report_type_short_name = factory.LazyAttribute(lambda x: x.definition["data_format"]["name"])
    short_name = factory.LazyAttribute(lambda x: x.definition["parser_name"])
    version = factory.LazyAttribute(lambda x: x.definition["version"])
