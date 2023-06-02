import factory
from core.models import DataSource, Identity, User
from faker import Faker

fake = Faker()


class DataSourceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DataSource

    short_name = factory.Faker('hostname')
    url = factory.Faker('url')


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('username',)

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda x: f"{x.username}@celus.test".lower())


class IdentityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Identity
        django_get_or_create = ('user',)

    user = factory.SubFactory(UserFactory)
    identity = factory.LazyAttribute(lambda x: x.user.email)
