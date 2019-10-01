import pytest

from core.tests.conftest import *
from organizations.models import UserOrganization
from organizations.tests.conftest import organizations


@pytest.fixture
def identity_by_user_type(admin_identity, invalid_identity, master_identity,
                          organizations, valid_identity):
    def fn(user_type):
        org = organizations[0]
        # we do not user admin_client, master_client, etc. because the way the fixtures work
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
                user_id=Identity.objects.get(identity=identity).user_id, organization=org,
                is_admin=False
            )
        elif user_type == 'related_admin':
            identity = valid_identity
            UserOrganization.objects.create(
                user_id=Identity.objects.get(identity=identity).user_id, organization=org,
                is_admin=True
            )
        elif user_type == 'master_user':
            identity = master_identity
        elif user_type == 'superuser':
            identity = admin_identity
        else:
            raise ValueError(f'Unsupported user_type: {user_type}')
        return identity, org
    return fn
