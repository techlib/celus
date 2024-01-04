import factory
from allauth.account.models import EmailAddress
from django_otp.plugins.otp_email.models import EmailDevice
from faker import Faker

from core.models import DataSource, Identity, User

fake = Faker()


class DataSourceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DataSource

    short_name = factory.Faker("hostname")
    url = factory.Faker("url")


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda x: f"{x.username}@celus.test".lower())


class IdentityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Identity
        django_get_or_create = ("user",)

    user = factory.SubFactory(UserFactory)
    identity = factory.LazyAttribute(lambda x: x.user.email)


class EmailAddressFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EmailAddress

    user = factory.SubFactory(UserFactory)
    email = factory.LazyAttribute(lambda x: x.user.email)


class EmailDeviceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EmailDevice

    name = "default"
    user = factory.SubFactory(UserFactory)
    email = factory.LazyAttribute(lambda x: x.user.email)
