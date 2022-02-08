import factory

from core.models import User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('username',)

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda x: f"{x.username}@celus.test".lower())
