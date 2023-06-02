import factory
from api.models import OrganizationAPIKey


class OrganizationAPIKeyFactory(factory.django.DjangoModelFactory):
    name = factory.Faker('name')
    prefix = factory.Faker('lexify', text="????????")
    id = factory.Faker('lexify')

    class Meta:
        model = OrganizationAPIKey
