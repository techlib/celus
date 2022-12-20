import factory
from faker import Faker
from organizations.models import Organization, OrganizationAltName

fake = Faker()


class OrganizationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Organization
        django_get_or_create = ('name',)

    ext_id = factory.Sequence(lambda n: n)
    ico = factory.Sequence(lambda n: n)
    name = factory.Faker('company')
    internal_id = factory.LazyAttribute(lambda x: x.name.upper().replace(' ', '_'))
    short_name = factory.LazyAttribute(lambda x: x.name[:10])
    url = factory.Faker('url')
    fte = factory.Faker('pyint')
    address = factory.LazyAttribute(lambda x: {'street': fake.street_address()})
    parent = None


class OrganizationAltNameFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrganizationAltName
        django_get_or_create = ('name',)

    name = factory.Faker('company')
    organization = factory.SubFactory(OrganizationFactory)
