import pytest
from django.urls import reverse

from core.models import User
from test_scenarios.basic import (  # noqa - fixtures
    basic1,
    clients,
    counter_report_types,
    credentials,
    data_sources,
    harvests,
    identities,
    import_batches,
    organizations,
    platforms,
    report_types,
    schedulers,
    users,
)


@pytest.mark.django_db
class TestAccessibleOrganizations:
    def test_counts(self, basic1, organizations, platforms, clients, users):
        assert User.objects.count() == 8, "we should have 8 test users and 5 orgs"
        assert users['user1'].organizations.count() == 1, "user 1 belongs to branch org"
        assert (
            users['user1'].accessible_organizations().count() == 1
        ), "only branch org accessible for user1"

        assert users['admin1'].organizations.count() == 2, "admin1 belongs to root and branch org"
        assert (
            users['admin1'].accessible_organizations().count() == 2
        ), "both root and branch org are accessible for admin1"

        assert users['user2'].organizations.count() == 1, "user2 belongs to standalone org"
        assert (
            users['user2'].accessible_organizations().count() == 1
        ), "standalone is accessible for user2"
        assert users['admin2'].organizations.count() == 1, "admin2 belongs to standalone org"
        assert (
            users['admin2'].accessible_organizations().count() == 1
        ), "standalone is accessible for user2"

        assert users['master_user'].organizations.count() == 1, "master_user belongs to master org"
        assert (
            users['master_user'].accessible_organizations().count() == 5
        ), "all organizations are accessible for master_user"
        assert (
            users['master_admin'].organizations.count() == 1
        ), "master_admin belongs to master org"
        assert (
            users['master_admin'].accessible_organizations().count() == 5
        ), "all organizations are accessible for master_admin"

        assert users['su'].organizations.count() == 0, "superuser doesn't explicitly belong to org"
        assert (
            users['su'].accessible_organizations().count() == 5
        ), "all organizations are accessible for superuser"

        assert (
            users['admin1'].userorganization_set.filter(organization__name="branch").delete()[0]
            == 1
        ), "remove admin1 from branch organization"
        assert users['admin1'].accessible_organizations().count() == 2, (
            "branch is a subbranch of root and are both org are accessible for admin1 "
            "even when admin1 is only direct member of root org"
        )


@pytest.mark.django_db
class TestAccessibleUsers:
    # superuser can see all users
    def test_superuser_access(self, basic1, organizations, platforms, clients, users):
        resp = clients['su'].get(reverse('user-management-list'))
        assert resp.status_code == 200
        assert len(resp.json()) == User.objects.count()

    # superuser can create users in all orgs
    @pytest.mark.parametrize('org', ['root', 'branch', 'standalone', 'master', 'empty'])
    def test_superuser_add_user(self, basic1, organizations, platforms, clients, users, org):
        resp = clients['su'].post(
            reverse('user-management-list'),
            data={
                'first_name': 'name',
                'last_name': 'name',
                'username': 'name',
                'email': 'name@email.com',
                'is_admin': False,
                'organization': organizations[org].pk,
            },
        )
        assert resp.status_code == 201

    # superuser can remove all users from orgs
    @pytest.mark.parametrize(
        ['user', 'org'],
        [
            ('user1', 'branch'),
            ('user2', 'standalone'),
            ('master_user', 'master'),
            ('master_admin', 'master'),
            ('admin1', 'root'),
            ('admin2', 'standalone'),
        ],
    )
    def test_superuser_delete_user(
        self, basic1, organizations, platforms, clients, users, user, org
    ):
        resp = clients['su'].post(
            reverse('user-management-delete-relation', args=[users[user].pk]),
            data={'organization': organizations[org].pk},
        )
        assert resp.status_code == 200, "superuser should be able to delete all users"

    # admin of master org can add to all orgs
    @pytest.mark.parametrize('org', ['root', 'branch', 'standalone', 'master'])
    def test_master_admin(self, basic1, organizations, platforms, clients, users, org):
        resp = clients['master_admin'].post(
            reverse('user-management-list'),
            data={
                'first_name': 'name',
                'last_name': 'name',
                'username': 'name',
                'email': 'name@email.com',
                'is_admin': False,
                'organization': organizations[org].pk,
            },
        )
        assert resp.status_code == 201, "admin of master org should be able to add to all orgs"

    # no user can delete himself
    @pytest.mark.parametrize(
        ['user', 'org'],
        [
            ('user1', 'branch'),
            ('user2', 'standalone'),
            ('master_user', 'master'),
            ('master_admin', 'master'),
            ('admin1', 'root'),
            ('admin2', 'standalone'),
            ('su', 'root'),
        ],
    )
    def test_delete_itself(self, basic1, organizations, platforms, clients, users, user, org):
        resp = clients[user].post(
            reverse('user-management-delete-relation', args=[users[user].pk]),
            data={'organization': organizations[org].pk},
        )
        assert resp.status_code == 403, "user should not be able to delete himself"

    # readonly users can only see themselves
    @pytest.mark.parametrize('user', ['user1', 'user2', 'master_user'])
    def test_readonly_users_get(self, basic1, organizations, platforms, clients, users, user):
        resp = clients[user].get(reverse('user-management-list'))
        assert resp.status_code == 200
        assert len(resp.json()) == 1, "read-only users should only see themselves"

    # read only users cannot add users
    @pytest.mark.parametrize('user', ['user1', 'user2', 'master_user'])
    def test_readonly_users_post(self, basic1, organizations, platforms, clients, users, user):
        resp = clients[user].post(
            reverse('user-management-list'),
            data={
                'first_name': 'name',
                'last_name': 'name',
                'username': 'name',
                'email': 'name@email.com',
                'is_admin': False,
                'organization': organizations['standalone'].pk,
            },
        )
        assert resp.status_code == 403, "read-only users should not be able to add users"

    # read only users cannot delete users
    @pytest.mark.parametrize(
        ['user', 'org'],
        [
            ('user1', 'branch'),
            ('user2', 'standalone'),
            ('master_user', 'master'),
            ('master_admin', 'master'),
            ('admin1', 'root'),
            ('admin2', 'standalone'),
            ('su', 'root'),
        ],
    )
    def test_readonly_users_delete(
        self, basic1, organizations, platforms, clients, users, user, org
    ):
        resp = clients[user].post(
            reverse('user-management-delete-relation', args=[users[user].pk]),
            data={'organization': organizations[org].pk},
        )
        assert resp.status_code == 403, "read-only users should not be able to delete users"

    # admin of non-master org cannot see superusers and master org admins
    @pytest.mark.parametrize('user', ['admin1', 'admin2'])
    def test_non_master_admin(self, basic1, organizations, platforms, clients, users, user):
        resp = clients[user].get(reverse('user-management-list'))
        print(resp.json())
        # cannot see any superuser
        assert not any(
            [user['is_superuser'] for user in resp.json()]
        ), "non-master admin should not be able to see superusers"
        # cannot see any master admin
        assert not any(
            [user['is_admin_of_master_organization'] for user in resp.json()]
        ), "non-master admin should not be able to see master admins"

    # test that users are sucessfully created and added to appropriate orgs and permissions
    def test_create(self, basic1, organizations, platforms, clients, users):
        users_count = User.objects.count()
        standalone_users_cnt = organizations['standalone'].users.all().count()

        # create non-admin user
        clients['su'].post(
            reverse('user-management-list'),
            data={
                'first_name': 'name',
                'last_name': 'name',
                'username': 'name',
                'email': 'name@email.com',
                'is_admin': False,
                'organization': organizations['standalone'].pk,
            },
        )

        # check that new user was created
        assert User.objects.count() == users_count + 1
        # check that new user was added to standalone org
        assert organizations['standalone'].users.all().count() == standalone_users_cnt + 1
        # check that new user was added as non-admin
        assert (
            organizations['standalone']
            .users.last()
            .has_organization_admin_permission(organizations['standalone'].pk)
            is False
        )

        # create admin user
        clients['admin2'].post(
            reverse('user-management-list'),
            data={
                'first_name': 'name2',
                'last_name': 'name2',
                'username': 'name2',
                'email': 'name2@email.com',
                'is_admin': True,
                'organization': organizations['standalone'].pk,
            },
        )

        assert User.objects.count() == users_count + 2
        assert organizations['standalone'].users.all().count() == standalone_users_cnt + 2
        assert (
            organizations['standalone']
            .users.last()
            .has_organization_admin_permission(organizations['standalone'].pk)
            is True
        )


@pytest.mark.django_db
class TestEmail:
    @pytest.mark.parametrize(
        'user', ['user1', 'user2', 'master_user', 'master_admin', 'admin1', 'admin2', 'su']
    )
    def test_send_verification_email(
        self, basic1, organizations, platforms, clients, users, mailoutbox, settings, user
    ):
        settings.ALLOW_EDUID_LOGIN = False
        assert len(mailoutbox) == 0
        resp = clients['su'].post(reverse('send_verification_email'), data={'pk': users[user].pk})
        assert resp.status_code == 200
        assert len(mailoutbox) == 1

    @pytest.mark.parametrize(
        'user', ['user1', 'user2', 'master_user', 'master_admin', 'admin1', 'admin2', 'su']
    )
    def test_send_invitation_email(
        self, basic1, organizations, platforms, clients, users, mailoutbox, settings, user, site
    ):
        settings.ALLOWED_HOSTS = ['testserver', site.domain]
        settings.ALLOW_EDUID_LOGIN = False
        assert len(mailoutbox) == 0
        resp = clients['su'].post(reverse('send_invitation_email'), data={'pk': users[user].pk})
        assert resp.status_code == 200
        assert len(mailoutbox) == 1
