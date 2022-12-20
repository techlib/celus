import pytest
from core.models import Identity
from core.tests.conftest import *  # noqa - fixtures

from test_fixtures.entities.organizations import OrganizationFactory

from ..models import Organization, UserOrganization


@pytest.fixture()
def organizations():
    parent1, _ = Organization.objects.get_or_create(
        ext_id=1,
        parent=None,
        internal_id='AAA',
        ico='123',
        name_cs='AAA',
        name_en='AAA',
        short_name='AA',
        raw_data_import_enabled=False,
    )
    parent2, _ = Organization.objects.get_or_create(
        ext_id=2,
        parent=None,
        internal_id='BBB',
        ico='234',
        name_cs='BBB',
        name_en='BBB',
        short_name='BB',
        raw_data_import_enabled=True,
    )
    child1, _ = Organization.objects.get_or_create(
        ext_id=3,
        parent=parent1,
        internal_id='AAA1',
        ico='1231',
        name_cs='AAA1',
        name_en='AAA1',
        short_name='AA1',
        raw_data_import_enabled=False,
    )
    return [parent1, parent2, child1]


@pytest.fixture()
def organizations_random():
    parent1 = OrganizationFactory.create()
    parent2 = OrganizationFactory.create()
    child1 = OrganizationFactory.create(parent=parent1)
    return [parent1, parent2, child1]


@pytest.fixture()
def organization_random():
    return OrganizationFactory.create()


@pytest.fixture
def identity_by_user_type(
    admin_identity,
    invalid_identity,
    master_user_identity,
    master_admin_identity,
    organizations,
    valid_identity,
):
    def fn(user_type):
        org = organizations[0]
        # we do not use admin_client, master_admin_client, etc. because the way the fixtures work
        # they all point to the same client object which obviously does not work
        if user_type == 'no_user':
            identity = None
        elif user_type == 'invalid':
            identity = invalid_identity
        elif user_type == 'unrelated':
            identity = valid_identity
        elif user_type == 'related_user':
            identity = valid_identity
            UserOrganization.objects.create(
                user_id=Identity.objects.get(identity=identity).user_id,
                organization=org,
                is_admin=False,
            )
        elif user_type == 'related_admin':
            identity = valid_identity
            UserOrganization.objects.create(
                user_id=Identity.objects.get(identity=identity).user_id,
                organization=org,
                is_admin=True,
            )
        elif user_type == 'master_user':
            identity = master_user_identity
        elif user_type == 'master_admin':
            identity = master_admin_identity
        elif user_type == 'superuser':
            identity = admin_identity
        else:
            raise ValueError(f'Unsupported user_type: {user_type}')
        return identity, org

    return fn


__all__ = ['identity_by_user_type', 'organizations', 'organizations_random']
