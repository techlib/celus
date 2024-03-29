import factory
from core.models import Identity
from faker import Faker

from .users import UserFactory

fake = Faker()


class IdentityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Identity
        django_get_or_create = ('user',)

    user = factory.SubFactory(UserFactory)
    identity = factory.LazyAttribute(lambda x: x.user.email)
