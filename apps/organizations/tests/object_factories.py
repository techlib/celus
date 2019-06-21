import factory
from faker import Faker

from ..models import Organization


fake = Faker()


class OrganizationFactory(factory.DjangoModelFactory):
    class Meta:
        model = Organization

    ext_id = factory.Sequence(lambda n: n)
    ico = factory.Sequence(lambda n: n)
    name = factory.Faker('company')
    internal_id = factory.LazyAttribute(lambda x: x.name.upper().replace(' ', '_'))
    short_name = factory.LazyAttribute(lambda x: x.name[:10])
    url = factory.Faker('url')
    fte = factory.Faker('pyint')
    address = factory.LazyAttribute(lambda x: {'street': fake.street_address()})
    parent = None
