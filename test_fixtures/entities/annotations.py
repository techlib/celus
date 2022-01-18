import factory

from faker import Faker
from annotations.models import Annotation

from .organizations import OrganizationFactory
from .platforms import PlatformFactory
from .users import UserFactory


fake = Faker()


class AnnotationFactory(factory.DjangoModelFactory):
    class Meta:
        model = Annotation

    platform = factory.SubFactory(PlatformFactory)
    organization = factory.SubFactory(OrganizationFactory)
    author = factory.SubFactory(UserFactory)

    subject = factory.Faker('word')
    subject_cs = factory.Faker('word', locale='cs_CZ')

    short_message = factory.Faker('words')
    short_message_cs = factory.Faker('words', locale='cs_CZ')

    message = factory.Faker('words')
    message_cs = factory.Faker('words', locale='cs_CZ')
