import factory
from annotations.models import Annotation
from core.fake_data import UserFactory
from faker import Faker
from organizations.fake_data import OrganizationFactory
from publications.fake_data import PlatformFactory

fake = Faker()


class AnnotationFactory(factory.django.DjangoModelFactory):
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
