import pytest
from core.models import DataSource
from django.db import IntegrityError
from organizations.models import OrganizationAltName


@pytest.mark.django_db
class TestOrganizationAltName:
    def test_name_uniqueness(self, organizations):
        OrganizationAltName.objects.create(organization=organizations[0], name='foo')
        with pytest.raises(IntegrityError):
            # cannot create alt name with the same name and same source
            OrganizationAltName.objects.create(organization=organizations[1], name='foo')

    def test_name_uniqueness_same_source(self, organizations):
        source = DataSource.objects.create(short_name='foo', type=DataSource.TYPE_API)
        OrganizationAltName.objects.create(organization=organizations[0], name='foo', source=source)
        with pytest.raises(IntegrityError):
            # cannot create alt name with the same name and same source
            OrganizationAltName.objects.create(
                organization=organizations[1], name='foo', source=source
            )

    def test_name_uniqueness_different_source(self, organizations):
        source = DataSource.objects.create(short_name='foo', type=DataSource.TYPE_API)
        OrganizationAltName.objects.create(organization=organizations[0], name='foo', source=source)
        # can create with a different source - null is implied bellow
        OrganizationAltName.objects.create(organization=organizations[1], name='foo')
