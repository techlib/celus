import factory

from faker import Faker
from publications.models import Platform


fake = Faker()


class PlatformFactory(factory.DjangoModelFactory):
    class Meta:
        model = Platform

    ext_id = factory.Sequence(lambda n: n)
    name = factory.Faker('name')
    short_name = factory.LazyAttribute(lambda x: x.name[:10])
    url = factory.Faker('url')
