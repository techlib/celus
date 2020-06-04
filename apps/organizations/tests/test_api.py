import pytest
from django.urls import reverse

from core.models import Identity
from organizations.models import UserOrganization
from core.tests.conftest import (
    authenticated_client,
    authentication_headers,
    invalid_identity,
    valid_identity,
)


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
