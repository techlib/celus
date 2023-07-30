import factory
from faker import Faker

from core.models import DataSource, Identity, User

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


# Mailchimp stuff
class Member:
    def __init__(
        self,
        id,
        first_name,
        last_name,
        email="",
        celus_installations=None,
        celus_address1="",
        celus_address2="",
        celus_address3="",
        tags=None,
    ):
        self.email = email
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        # MMERGE6
        self.celus_installations = celus_installations if celus_installations else []
        # MMERGE7
        self.celus_address1 = celus_address1
        # MMERGE8
        self.celus_address2 = celus_address2
        # MMERGE9
        self.celus_address3 = celus_address3
        self.tags = tags if tags else []
        self.perform = None


class MemberFactory(factory.Factory):
    class Meta:
        model = Member

    id = factory.Faker('uuid4')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = "user@celus.test"
