import pytest

from ..models import Organization
from .object_factories import OrganizationFactory


@pytest.mark.django_db
class TestDb(object):
    def test_organization_factory(self):
        assert Organization.objects.count() == 0
        OrganizationFactory.create()
        OrganizationFactory.create()
        assert Organization.objects.count() == 2

    def test_organization_str(self):
        org = OrganizationFactory.create()
        assert str(org) == org.name
