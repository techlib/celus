import pytest
from rest_framework.exceptions import PermissionDenied

from core.models import UL_CONS_ADMIN, UL_ORG_ADMIN, UL_CONS_STAFF, Identity
from organizations.models import UserOrganization
from sushi.logic.data_import import import_sushi_credentials
from ..models import SushiCredentials
from publications.models import Platform
from organizations.tests.conftest import organizations
from publications.tests.conftest import platforms
from core.tests.conftest import master_identity, valid_identity


@pytest.mark.now
@pytest.mark.django_db
class TestLocking(object):

    @pytest.mark.parametrize(['user_code', 'can_lock_super', 'can_lock_staff',
                              'can_lock_org_admin'],
                             (('org_admin', False, False, True),
                              ('staff', False, True, True),
                              ('superuser', True, True, True),
                             ))
    def test_can_lock_to_level_permissions(self, admin_user, master_identity, valid_identity,
                                           organizations, platforms,
                                           user_code, can_lock_super, can_lock_org_admin,
                                           can_lock_staff):

        org = organizations[0]
        credentials = SushiCredentials.objects.create(
            organization=org,
            platform=platforms[0],
            counter_version=5,
        )
        user = self._user_code_to_user(user_code, org, admin_user, master_identity, valid_identity)
        self._test_change_lock(credentials, user, UL_ORG_ADMIN, can_lock_org_admin)
        credentials.lock_level = 0
        credentials.save()
        self._test_change_lock(credentials, user, UL_CONS_STAFF, can_lock_staff)
        credentials.lock_level = 0
        credentials.save()
        self._test_change_lock(credentials, user, UL_CONS_ADMIN, can_lock_super)

    @pytest.mark.parametrize(['user_code', 'can_unlock_super', 'can_unlock_staff',
                              'can_unlock_org_admin'],
                             (('org_admin', False, False, True),
                              ('staff', False, True, True),
                              ('superuser', True, True, True),
                             ))
    def test_can_unlock_from_level(
            self, admin_user, master_identity, valid_identity, organizations, platforms,
            user_code, can_unlock_super, can_unlock_org_admin, can_unlock_staff):
        org = organizations[0]
        credentials = SushiCredentials.objects.create(
            organization=org,
            platform=platforms[0],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
        )
        user = self._user_code_to_user(user_code, org, admin_user, master_identity, valid_identity)
        self._test_change_lock(credentials, user, 0, can_unlock_org_admin)
        credentials.lock_level = UL_CONS_STAFF
        credentials.save()
        self._test_change_lock(credentials, user, 0, can_unlock_staff)
        credentials.lock_level = UL_CONS_ADMIN
        credentials.save()
        self._test_change_lock(credentials, user, 0, can_unlock_super)

    @classmethod
    def _user_code_to_user(cls, code: str, organization, admin_user, master_identity,
                           valid_identity):
        if code == 'org_admin':
            user = Identity.objects.get(identity=valid_identity).user
            UserOrganization.objects.create(user=user, organization=organization, is_admin=True)
            return user
        elif code == 'superuser':
            return admin_user
        elif code == 'staff':
            return Identity.objects.get(identity=master_identity).user
        raise ValueError(f'wrong code {code}')

    @classmethod
    def _test_change_lock(cls, credentials, user, level, can):
        if can:
            credentials.change_lock(user, level)
            assert credentials.lock_level == level
        else:
            with pytest.raises(PermissionDenied):
                credentials.change_lock(user, level)



