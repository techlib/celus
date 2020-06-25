import pytest
from django.urls import reverse

from core.models import Identity, User
from organizations.models import UserOrganization, Organization
from core.tests.conftest import (
    authenticated_client,
    authentication_headers,
    invalid_identity,
    valid_identity,
)
from organizations.views import OrganizationViewSet


@pytest.mark.django_db
class TestOrganizationAPI(object):
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

    @pytest.mark.now
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
        assert org in authenticated_client.user.organizations.all()
        assert (
            org.private_data_source == org.source
        ), 'organization object data source should be the organizations own private data-source'
        userorg = UserOrganization.objects.get(organization=org, user=authenticated_client.user)
        assert (
            org.private_data_source == userorg.source
        ), 'user-organization data source should be the organizations own private data-source'

    @pytest.mark.now
    def test_user_default_organization_creation_not_allowed(self, authenticated_client, settings):
        settings.ALLOW_USER_REGISTRATION = False
        url = reverse('organization-create-user-default')
        assert Organization.objects.count() == 0
        resp = authenticated_client.post(
            url, {'name': 'test organization'}, content_type='application/json'
        )
        assert resp.status_code == 400
        assert Organization.objects.count() == 0

    @pytest.mark.now
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

    @pytest.mark.now
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
