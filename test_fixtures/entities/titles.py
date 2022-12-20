import factory
from faker import Faker
from publications.models import Title

fake = Faker()


class TitleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Title
        django_get_or_create = ('name', 'isbn')

    name = factory.Faker('sentence')
    isbn = factory.Faker('isbn13', separator='')
