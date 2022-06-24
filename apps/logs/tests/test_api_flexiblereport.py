import pytest
from core.logic.serialization import b64json
from django.urls import reverse
from logs.models import FlexibleReport
from organizations.models import UserOrganization
from organizations.tests.conftest import organizations  # noqa
from test_fixtures.scenarios.basic import users  # noqa


@pytest.mark.django_db
class TestFlexibleReportAPI:
    def test_list_simple(self, admin_client):
        url = reverse('flexible-report-list')
        resp = admin_client.get(url)
        assert resp.status_code == 200

    @pytest.mark.parametrize(
        ['user', 'accessible_reports'],
        [
            ['user1', {'public', 'user1 report'}],
            ['user2', {'public', 'user2 report'}],
            ['admin1', {'public', 'org1 report'}],
            ['admin2', {'public', 'org2 report'}],
            ['empty', {'public', 'org1 report', 'org2 report'}],
            ['master_admin', {'public'}],
            ['master_user', {'public'}],
            ['su', {'public', 'org1 report', 'org2 report'}],  # cannot see private
        ],
    )
    def test_list_access(self, client, users, organizations, user, accessible_reports):
        organization1 = organizations[0]
        organization2 = organizations[1]
        FlexibleReport.objects.create(name='public')
        FlexibleReport.objects.create(name='user1 report', owner=users['user1'])
        FlexibleReport.objects.create(name='user2 report', owner=users['user2'])
        FlexibleReport.objects.create(name='org1 report', owner_organization=organization1)
        FlexibleReport.objects.create(name='org2 report', owner_organization=organization2)
        UserOrganization.objects.create(user=users['admin1'], organization=organization1)
        UserOrganization.objects.create(user=users['admin2'], organization=organization2)
        UserOrganization.objects.create(user=users['empty'], organization=organization1)
        UserOrganization.objects.create(user=users['empty'], organization=organization2)

        url = reverse('flexible-report-list')
        client.force_login(users[user])
        resp = client.get(url)
        assert resp.status_code == 200
        assert accessible_reports == {rec['name'] for rec in resp.json()}

    def test_create(self, admin_client, admin_user):
        resp = admin_client.post(
            reverse('flexible-report-list'),
            {
                'name': 'test report',
                'config': {'primary_dimension': 'platform', 'groups': b64json(['metric'])},
            },
            content_type='application/json',
        )
        assert resp.status_code == 201
        report = FlexibleReport.objects.get(pk=resp.json()['pk'])
        assert report.owner == admin_user
        assert report.owner_organization is None
        assert report.last_updated_by == admin_user
        assert report.report_config['primary_dimension'] == 'platform'
        assert report.report_config['group_by'] == ['metric']

    @pytest.fixture()
    def user_organizations(self, users, organizations):
        org1 = organizations[0]
        org2 = organizations[1]
        UserOrganization.objects.create(user=users['user1'], organization=org1)
        UserOrganization.objects.create(user=users['user2'], organization=org2)
        UserOrganization.objects.create(user=users['admin1'], organization=org1, is_admin=True)
        UserOrganization.objects.create(user=users['admin2'], organization=org2, is_admin=True)
        UserOrganization.objects.create(
            user=users['master_admin'], organization=org1, is_admin=True
        )
        UserOrganization.objects.create(
            user=users['master_admin'], organization=org2, is_admin=True
        )

    @pytest.mark.parametrize(
        ['user', 'can_private', 'can_org1', 'can_org2', 'can_consortium'],
        [
            #         private, org1, org2, consortium
            ['user1', True, False, False, False],  # normal user, connected to org1
            ['user2', True, False, False, False],  # normal user, connected to org2
            ['admin1', True, True, False, False],  # admin of org1
            ['admin2', True, False, True, False],  # admin of org2
            ['master_admin', True, True, True, False],  # admin of org1 and org2
            ['master_user', True, False, False, False],  # only private
            ['su', True, True, True, True],  # superuser
        ],
    )
    def test_create_accesslevel(
        self,
        client,
        users,
        organizations,
        user_organizations,
        user,
        can_private,
        can_org1,
        can_org2,
        can_consortium,
    ):
        """
        Test that when saving a report the user can/cannot set a specific accesslevel
        and also for specific organization when setting organization level access
        """
        org1 = organizations[0]
        org2 = organizations[1]
        data_base = {
            'name': 'test report',
            'config': {'primary_dimension': 'platform', 'groups': b64json(['metric'])},
        }
        url = reverse('flexible-report-list')
        client.force_login(users[user])

        # private
        resp = client.post(url, data_base, content_type='application/json')
        assert resp.status_code == (201 if can_private else 403)
        assert resp.json()['owner'] == users[user].pk
        assert resp.json()['owner_organization'] is None

        # org1
        resp = client.post(
            url,
            {**data_base, 'owner_organization': org1.pk, 'owner': None},
            content_type='application/json',
        )
        assert resp.status_code == (201 if can_org1 else 403)
        if can_org1:
            assert resp.json()['owner'] is None
            assert resp.json()['owner_organization'] == org1.pk

        # org2
        resp = client.post(
            url,
            {**data_base, 'owner_organization': org2.pk, 'owner': None},
            content_type='application/json',
        )
        assert resp.status_code == (201 if can_org2 else 403)
        if can_org2:
            assert resp.json()['owner'] is None
            assert resp.json()['owner_organization'] == org2.pk

        # consortium
        resp = client.post(url, {**data_base, 'owner': None}, content_type='application/json')
        assert resp.status_code == (201 if can_consortium else 403)
        if can_consortium:
            assert resp.json()['owner'] is None
            assert resp.json()['owner_organization'] is None

    @classmethod
    def access_to_code(cls, access, delete=False):
        if access is None:
            return 404
        elif access:
            return 204 if delete else 200
        return 403

    @pytest.fixture(params=["user1", "user2", "org1", "org2", "admin1", "admin2", "consortium"])
    def flexible_report(self, request, organizations, users):
        data = {'report_config': {'primary_dimension': 'platform', 'group_by': ['metric']}}
        if request.param in ('user1', 'user2', 'admin1', 'admin2'):
            # user owned
            data['owner'] = users[request.param]
        elif request.param == 'org1':
            # organization owned
            data['owner_organization'] = organizations[0]
        elif request.param == 'org2':
            # organization owned
            data['owner_organization'] = organizations[1]
        elif request.param == 'consortium':
            # consortium owned
            data['owner'] = None
        return {
            'level': request.param,
            'report': FlexibleReport.objects.create(name=f'test {request.param}', **data),
        }

    @pytest.mark.parametrize(
        ['user', 'can'],
        [
            #         change_spec, private, org1, org2, consortium (None => cannot see)
            [
                'user1',  # normal user, connected to org1
                {
                    'user1': (True, True, False, False, False),  # what he can do to report user1
                    'user2': (None, None, None, None, None),  # what he can do to report user2
                    'admin1': (None, None, None, None, None),  # what he can do to report admin1
                    'admin2': (None, None, None, None, None),  # what he can do to report admin2
                    'org1': (False, False, False, False, False),  # what he can do to report org1
                    'org2': (None, None, None, None, None),  # what he can do to report org2
                    'consortium': (False, False, False, False, False),  # what he can do to cons...
                },
            ],
            [
                'user2',  # normal user, connected to org2
                {
                    'user1': (None, None, None, None, None),  # what he can do to report user1
                    'user2': (True, True, False, False, False),  # what he can do to report user2
                    'admin1': (None, None, None, None, None),  # what he can do to report admin1
                    'admin2': (None, None, None, None, None),  # what he can do to report admin2
                    'org1': (None, None, None, None, None),  # what he can do to report org1
                    'org2': (False, False, False, False, False),  # what he can do to report org2
                    'consortium': (False, False, False, False, False),  # what he can do to cons...
                },
            ],
            [
                'admin1',  # admin of org1
                {
                    'user1': (None, None, None, None, None),  # what he can do to report user1
                    'user2': (None, None, None, None, None),  # what he can do to report user2
                    'admin1': (True, True, True, False, False),  # what he can do to report admin1
                    'admin2': (None, None, None, None, None),  # what he can do to report admin2
                    'org1': (True, True, True, False, False),  # what he can do to report org1
                    'org2': (None, None, None, None, None),  # what he can do to report org2
                    'consortium': (False, False, False, False, False),  # what he can do to cons...
                },
            ],
            [
                'admin2',  # admin of org2
                {
                    'user1': (None, None, None, None, None),  # what he can do to report user1
                    'user2': (None, None, None, None, None),  # what he can do to report user2
                    'admin1': (None, None, None, None, None),  # what he can do to report admin1
                    'admin2': (True, True, False, True, False),  # what he can do to report admin2
                    'org1': (None, None, None, None, None),  # what he can do to report org1
                    'org2': (True, True, False, True, False),  # what he can do to report org2
                    'consortium': (False, False, False, False, False),  # what he can do to cons...
                },
            ],
            [
                'master_admin',  # admin of org1 and org2
                {
                    'user1': (None, None, None, None, None),  # what he can do to report user1
                    'user2': (None, None, None, None, None),  # what he can do to report user2
                    'admin1': (None, None, None, None, None),  # what he can do to report admin1
                    'admin2': (None, None, None, None, None),  # what he can do to report admin2
                    'org1': (True, True, True, True, False),  # what he can do to report org1
                    'org2': (True, True, True, True, False),  # what he can do to report org2
                    'consortium': (False, False, False, False, False),  # what he can do to cons...
                },
            ],
            [
                'master_user',  # user of org1 and org2
                {
                    'user1': (None, None, None, None, None),  # what he can do to report user1
                    'user2': (None, None, None, None, None),  # what he can do to report user2
                    'admin1': (None, None, None, None, None),  # what he can do to report admin1
                    'admin2': (None, None, None, None, None),  # what he can do to report admin2
                    'org1': (None, None, None, None, None),  # what he can do to report org1
                    'org2': (None, None, None, None, None),  # what he can do to report org2
                    'consortium': (False, False, False, False, False),  # what he can do to cons...
                },
            ],
            [
                'su',  # superuser
                {
                    'user1': (None, None, None, None, None),  # what he can do to report user1
                    'user2': (None, None, None, None, None),  # what he can do to report user2
                    'admin1': (None, None, None, None, None),  # what he can do to report admin1
                    'admin2': (None, None, None, None, None),  # what he can do to report admin2
                    'org1': (True, True, True, True, True),  # what he can do to report org1
                    'org2': (True, True, True, True, True),  # what he can do to report org2
                    'consortium': (True, True, True, True, True),  # what he can do to cons...
                },
            ],
        ],
    )
    def test_update_accesslevel(
        self, client, users, organizations, user_organizations, user, flexible_report, can
    ):
        """
        Test that when updating a report with specific access level, the user can/cannot
        change the definition and/or access level.
        """
        org1 = organizations[0]
        org2 = organizations[1]
        fr = flexible_report['report']
        url = reverse('flexible-report-detail', args=(fr.pk,))
        client.force_login(users[user])
        can_change_spec, can_private, can_org1, can_org2, can_consortium = can[
            flexible_report['level']
        ]

        # change spec
        resp = client.patch(url, {'name': 'foobar'}, content_type='application/json')
        assert resp.status_code == self.access_to_code(can_change_spec)
        if can_change_spec:
            assert resp.json()['owner'] == fr.owner_id
            assert resp.json()['owner_organization'] == fr.owner_organization_id

        # private
        resp = client.patch(
            url,
            {'owner': users[user].pk, 'owner_organization': None},
            content_type='application/json',
        )
        assert resp.status_code == self.access_to_code(can_private)
        if can_private:
            assert resp.json()['owner'] == users[user].pk
            assert resp.json()['owner_organization'] is None

        # org1
        resp = client.patch(
            url, {'owner_organization': org1.pk, 'owner': None}, content_type='application/json'
        )
        assert resp.status_code == self.access_to_code(can_org1)
        if can_org1:
            assert resp.json()['owner'] is None
            assert resp.json()['owner_organization'] == org1.pk

        # org2
        resp = client.patch(
            url, {'owner_organization': org2.pk, 'owner': None}, content_type='application/json'
        )
        assert resp.status_code == self.access_to_code(can_org2)
        if can_org2:
            assert resp.json()['owner'] is None
            assert resp.json()['owner_organization'] == org2.pk

        # consortium
        resp = client.patch(
            url, {'owner_organization': None, 'owner': None}, content_type='application/json'
        )
        assert resp.status_code == self.access_to_code(can_consortium)
        if can_consortium:
            assert resp.json()['owner'] is None
            assert resp.json()['owner_organization'] is None

    @pytest.mark.parametrize(
        ['user', 'can'],
        [
            #         change_spec, private, org1, org2, consortium (None => cannot see)
            [
                'user1',  # normal user, connected to org1
                {
                    'user1': True,  # what he can do to report user1
                    'user2': None,  # what he can do to report user2
                    'admin1': None,  # what he can do to report admin1
                    'admin2': None,  # what he can do to report admin2
                    'org1': False,  # what he can do to report org1
                    'org2': None,  # what he can do to report org2
                    'consortium': False,  # what he can do to cons...
                },
            ],
            [
                'user2',  # normal user, connected to org2
                {
                    'user1': None,  # what he can do to report user1
                    'user2': True,  # what he can do to report user2
                    'admin1': None,  # what he can do to report admin1
                    'admin2': None,  # what he can do to report admin2
                    'org1': None,  # what he can do to report org1
                    'org2': False,  # what he can do to report org2
                    'consortium': False,  # what he can do to cons...
                },
            ],
            [
                'admin1',  # admin of org1
                {
                    'user1': None,  # what he can do to report user1
                    'user2': None,  # what he can do to report user2
                    'admin1': True,  # what he can do to report admin1
                    'admin2': None,  # what he can do to report admin2
                    'org1': True,  # what he can do to report org1
                    'org2': None,  # what he can do to report org2
                    'consortium': False,  # what he can do to cons...
                },
            ],
            [
                'admin2',  # admin of org2
                {
                    'user1': None,  # what he can do to report user1
                    'user2': None,  # what he can do to report user2
                    'admin1': None,  # what he can do to report admin1
                    'admin2': True,  # what he can do to report admin2
                    'org1': None,  # what he can do to report org1
                    'org2': True,  # what he can do to report org2
                    'consortium': False,  # what he can do to cons...
                },
            ],
            [
                'master_admin',  # admin of org1 and org2
                {
                    'user1': None,  # what he can do to report user1
                    'user2': None,  # what he can do to report user2
                    'admin1': None,  # what he can do to report admin1
                    'admin2': None,  # what he can do to report admin2
                    'org1': True,  # what he can do to report org1
                    'org2': True,  # what he can do to report org2
                    'consortium': False,  # what he can do to cons...
                },
            ],
            [
                'master_user',  # user of org1 and org2
                {
                    'user1': None,  # what he can do to report user1
                    'user2': None,  # what he can do to report user2
                    'admin1': None,  # what he can do to report admin1
                    'admin2': None,  # what he can do to report admin2
                    'org1': None,  # what he can do to report org1
                    'org2': None,  # what he can do to report org2
                    'consortium': False,  # what he can do to cons...
                },
            ],
            [
                'su',  # superuser
                {
                    'user1': None,  # what he can do to report user1
                    'user2': None,  # what he can do to report user2
                    'admin1': None,  # what he can do to report admin1
                    'admin2': None,  # what he can do to report admin2
                    'org1': True,  # what he can do to report org1
                    'org2': True,  # what he can do to report org2
                    'consortium': True,  # what he can do to cons...
                },
            ],
        ],
    )
    def test_delete_accesslevel(
        self, client, users, user_organizations, user, flexible_report, can
    ):
        """
        Test that when updating a report with specific access level, the user can/cannot
        change the definition and/or access level.
        """
        fr = flexible_report['report']
        url = reverse('flexible-report-detail', args=(fr.pk,))
        client.force_login(users[user])
        can_delete = can[flexible_report['level']]

        resp = client.delete(url)
        assert resp.status_code == self.access_to_code(can_delete, delete=True)
        if can_delete:
            assert FlexibleReport.objects.count() == 0
        else:
            assert FlexibleReport.objects.count() == 1
