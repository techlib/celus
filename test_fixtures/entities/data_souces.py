import factory

from faker import Faker
from core.models import DataSource


fake = Faker()


class DataSourceFactory(factory.DjangoModelFactory):
    class Meta:
        model = DataSource

    short_name = factory.Faker('ds')
    url = factory.Faker('url')
