import factory
from core.models import DataSource
from faker import Faker

fake = Faker()


class DataSourceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DataSource

    short_name = factory.Faker('ds')
    url = factory.Faker('url')
