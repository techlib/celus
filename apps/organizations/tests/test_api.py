import pytest
from core.models import Identity, User
from core.tests.conftest import authenticated_client  # noqa - fixtures
from core.tests.conftest import authentication_headers, invalid_identity, valid_identity
from django.urls import reverse
from logs.models import AccessLog, ImportBatch, Metric
from organizations.models import Organization, UserOrganization
from publications.tests.conftest import interest_rt  # noqa - fixture


@pytest.mark.django_db
class TestOrganizationAPI:
    def test_unauthorized_user(self, client, invalid_identity, authentication_headers):
        resp = client.get(reverse('organization-list'), **authentication_headers(invalid_identity))
        assert resp.status_code in (403, 401)  # depends on auth backend

    def test_authorized_user_no_orgs(self, authenticated_client):
        resp = authenticated_client.get(reverse('organization-list'))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_authorized_user_no_authorization(self, authenticated_client, organizations):
        """
        User is authenticated but does not belong to any org - the list should be empty
        :param authenticated_client:
        :param organizations:
        :return:
        """
        resp = authenticated_client.get(reverse('organization-list'))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_authorized_user_part_authorization(
        self, authenticated_client, organizations, valid_identity
    ):
        """
        User is authenticated but does not belong to any org - the list should be empty
        """
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations[1])
        resp = authenticated_client.get(reverse('organization-list'))
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]['pk'] == organizations[1].pk

    def test_authorized_user_no_authorization_detail(self, authenticated_client, organizations):
        """
        User is authenticated but does not belong to any org - the list should be empty
        :param authenticated_client:
        :param organizations:
        :return:
        """
        resp = authenticated_client.get(reverse('organization-detail', args=[organizations[0].pk]))
        assert resp.status_code == 404

    def test_user_default_organization_creation(self, authenticated_client, settings):
        settings.ALLOW_USER_REGISTRATION = True
        url = reverse('organization-create-user-default')
        assert Organization.objects.count() == 0
        resp = authenticated_client.post(
            url, {'name': 'test organization'}, content_type='application/json'
        )
        assert resp.status_code == 201
        assert Organization.objects.count() == 1
        org = Organization.objects.get()
        assert org.name == 'test organization'
        # All language mutations are supposed to be set to the same name
        assert org.name_en == 'test organization'
        assert org.name_cs == 'test organization'
        assert org.internal_id == 'test#test-organization'
        assert org in authenticated_client.user.organizations.all()
        assert (
            org.private_data_source == org.source
        ), 'organization object data source should be the organizations own private data-source'
        userorg = UserOrganization.objects.get(organization=org, user=authenticated_client.user)
        assert (
            org.private_data_source == userorg.source
        ), 'user-organization data source should be the organizations own private data-source'

    def test_user_default_organization_creation_not_allowed(self, authenticated_client, settings):
        settings.ALLOW_USER_REGISTRATION = False
        url = reverse('organization-create-user-default')
        assert Organization.objects.count() == 0
        resp = authenticated_client.post(
            url, {'name': 'test organization'}, content_type='application/json'
        )
        assert resp.status_code == 400
        assert Organization.objects.count() == 0

    def test_user_default_organization_creation_twice(self, authenticated_client, settings):
        settings.ALLOW_USER_REGISTRATION = True
        url = reverse('organization-create-user-default')
        assert Organization.objects.count() == 0
        resp = authenticated_client.post(
            url, {'name': 'test organization'}, content_type='application/json'
        )
        assert resp.status_code == 201
        assert Organization.objects.count() == 1
        # second time
        resp = authenticated_client.post(
            url, {'name': 'test organization'}, content_type='application/json'
        )
        assert resp.status_code == 400, 'only one organization per user'
        assert Organization.objects.count() == 1

    def test_user_default_organization_different_users(
        self, admin_client, authenticated_client, settings
    ):
        settings.ALLOW_USER_REGISTRATION = True
        url = reverse('organization-create-user-default')
        assert Organization.objects.count() == 0
        resp = admin_client.post(
            url, {'name': 'test organization'}, content_type='application/json'
        )
        assert resp.status_code == 201
        assert Organization.objects.count() == 1
        # second time
        resp = authenticated_client.post(
            url, {'name': 'test organization'}, content_type='application/json'
        )
        assert resp.status_code == 201, 'no problem for different user'
        assert Organization.objects.count() == 2
        # each user should have one organization
        assert authenticated_client.user.organizations.count() == 1
        admin_user = User.objects.get(is_superuser=True)
        assert admin_user.organizations.count() == 1

    def test_organization_interest_no_data(self, master_user_client, interest_rt):
        """
        Test the `interest` custom action of organization ViewSet without any data
        """
        resp = master_user_client.get(reverse('organization-interest', args=('-1',)))
        assert resp.status_code == 200
        assert resp.json() == {'days': 0, 'interest_sum': None, 'max_date': None, 'min_date': None}

    def test_organization_interest_data(self, master_user_client, interest_rt):
        """
        Test the `interest` custom action of organization ViewSet with some data
        """
        metric = Metric.objects.create(short_name='a', name='a')
        ib = ImportBatch.objects.create(report_type=interest_rt)
        AccessLog.objects.create(
            report_type=interest_rt, value=5, date='2020-01-01', metric=metric, import_batch=ib
        )
        resp = master_user_client.get(reverse('organization-interest', args=('-1',)))
        assert resp.status_code == 200
        assert resp.json() == {
            'days': 31,
            'interest_sum': 5,
            'max_date': '2020-01-31',
            'min_date': '2020-01-01',
        }

    def test_organization_interest_data_organizations(
        self, master_user_client, interest_rt, organizations
    ):
        """
        Test the `interest` custom action of organization ViewSet with some data and a specific
        organization
        """
        metric = Metric.objects.create(short_name='a', name='a')
        ib = ImportBatch.objects.create(report_type=interest_rt)
        AccessLog.objects.create(
            report_type=interest_rt,
            value=5,
            date='2020-01-01',
            metric=metric,
            import_batch=ib,
            organization=organizations[0],
        )
        AccessLog.objects.create(
            report_type=interest_rt,
            value=7,
            date='2020-02-01',
            metric=metric,
            import_batch=ib,
            organization=organizations[1],
        )
        resp = master_user_client.get(reverse('organization-interest', args=(organizations[0].pk,)))
        assert resp.status_code == 200
        assert resp.json() == {
            'days': 31,
            'interest_sum': 5,
            'max_date': '2020-01-31',
            'min_date': '2020-01-01',
        }
        resp = master_user_client.get(reverse('organization-interest', args=(organizations[1].pk,)))
        assert resp.status_code == 200
        assert resp.json() == {
            'days': 29,
            'interest_sum': 7,
            'max_date': '2020-02-29',
            'min_date': '2020-02-01',
        }
