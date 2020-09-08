from copy import deepcopy

import pytest
from django.contrib.auth import get_user_model

from core.logic.sync import sync_identities
from core.models import Identity, DataSource
from erms.sync import ERMSObjectSyncer
from organizations.models import Organization, UserOrganization
from ..logic.sync import sync_users


@pytest.fixture
def data_source():
    return DataSource.objects.create(type=DataSource.TYPE_API, short_name='test source')


@pytest.mark.django_db
class TestUserSync:

    user_data = [
        {'id': 1, 'vals': {'name@cs': ['Pepa Vonasek']}, 'refs': {'administrator of': [5]}},
        {'id': 22, 'vals': {'name@cs': ['Lojza Huml']}, 'refs': {'administrator of': []}},
        {'id': 333, 'vals': {'name@en': ['Jack Sparrow']},},
    ]

    def test_sync_users(self, data_source):
        User = get_user_model()
        assert User.objects.count() == 0
        stats = sync_users(data_source, self.user_data)
        assert stats['removed'][0] == 0
        assert stats[ERMSObjectSyncer.Status.NEW] == 3
        assert User.objects.count() == 3
        assert {u.ext_id for u in User.objects.all()} == {1, 22, 333}
        u1 = User.objects.get(ext_id=1)
        assert u1.first_name == 'Pepa'
        assert u1.last_name == 'Vonasek'
        assert u1.username == 'Pepa Vonasek1'
        u3 = User.objects.get(ext_id=333)
        assert u3.first_name == ''
        assert u3.last_name == ''
        assert u3.username == '333'

    def test_sync_users_resync(self, data_source):
        User = get_user_model()
        assert User.objects.count() == 0
        stats = sync_users(data_source, self.user_data)
        assert stats['removed'][0] == 0
        assert stats[ERMSObjectSyncer.Status.NEW] == 3
        assert User.objects.count() == 3
        stats = sync_users(data_source, self.user_data)
        assert stats['removed'][0] == 0
        assert stats[ERMSObjectSyncer.Status.NEW] == 0
        assert stats[ERMSObjectSyncer.Status.UNCHANGED] == 3
        assert User.objects.count() == 3

    def test_sync_users_with_removal(self, data_source):
        User = get_user_model()
        assert User.objects.count() == 0
        stats = sync_users(data_source, self.user_data)
        assert stats['removed'][0] == 0
        assert stats[ERMSObjectSyncer.Status.NEW] == 3
        assert User.objects.count() == 3
        stats = sync_users(data_source, self.user_data[:2])  # exclude the last record
        assert stats[ERMSObjectSyncer.Status.NEW] == 0
        assert stats[ERMSObjectSyncer.Status.UNCHANGED] == 2
        assert stats['removed'][0] == 1
        assert User.objects.count() == 2

    @pytest.mark.now
    def test_sync_users_with_user_org_link_removal(self, data_source):
        """
        Test that after a user gets removed from an organization, the link is properly removed
        """
        User = get_user_model()
        assert User.objects.count() == 0
        Organization.objects.create(ext_id=10, name='Org 1', short_name='org_1')
        Organization.objects.create(ext_id=100, name='Org 2', short_name='org_2')
        input_data = [
            {'id': 1, 'vals': {'name@cs': ['John Doe']}, 'refs': {'employee of': [10, 100]}},
        ]
        stats = sync_users(data_source, input_data)
        assert stats['removed'][0] == 0
        assert stats[ERMSObjectSyncer.Status.NEW] == 1
        assert User.objects.count() == 1
        assert UserOrganization.objects.count() == 2
        # now remove one of the organizations
        input_data[0]['refs']['employee of'].remove(10)
        stats = sync_users(data_source, input_data)
        assert stats[ERMSObjectSyncer.Status.NEW] == 0
        assert stats[ERMSObjectSyncer.Status.UNCHANGED] == 1
        assert stats['removed'][0] == 0
        assert stats['User-Org deleted'] == 1
        assert User.objects.count() == 1
        assert UserOrganization.objects.count() == 1


@pytest.mark.django_db
class TestIdentitySync:

    identity_data = [
        {'person': 1, 'identity': 'foo@bar.baz',},
        {'person': 1, 'identity': 'foo@baz.bar',},
        {'person': 22, 'identity': 'X',},
    ]

    def test_sync_identities(self, data_source):
        User = get_user_model()
        assert User.objects.count() == 0
        u1 = User.objects.create(ext_id=1, username='Foo Bar')
        u2 = User.objects.create(ext_id=22, username='XX')
        assert Identity.objects.count() == 0
        stats = sync_identities(data_source, self.identity_data)
        assert Identity.objects.count() == 3
        u1.refresh_from_db()
        u2.refresh_from_db()
        assert u1.identity_set.count() == 2
        assert u2.identity_set.count() == 1
        assert stats[ERMSObjectSyncer.Status.NEW] == 3

    def test_sync_identities_resync(self, data_source):
        User = get_user_model()
        assert User.objects.count() == 0
        u1 = User.objects.create(ext_id=1, username='Foo Bar')
        u2 = User.objects.create(ext_id=22, username='XX')
        assert Identity.objects.count() == 0
        sync_identities(data_source, self.identity_data)
        assert Identity.objects.count() == 3
        stats = sync_identities(data_source, self.identity_data)
        assert Identity.objects.count() == 3
        assert stats[ERMSObjectSyncer.Status.NEW] == 0
        assert stats[ERMSObjectSyncer.Status.UNCHANGED] == 3
        u1.refresh_from_db()
        u2.refresh_from_db()
        assert u1.identity_set.count() == 2  # should not change
        assert u2.identity_set.count() == 1  # should not change
