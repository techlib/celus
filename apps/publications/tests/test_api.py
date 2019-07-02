import pytest
from django.urls import reverse

from core.models import Identity
from logs.models import OrganizationPlatform
from organizations.models import UserOrganization
from organizations.tests.conftest import organizations
from core.tests.conftest import valid_identity, authenticated_client, authentication_headers,\
    invalid_identity


@pytest.mark.django_db
class TestPlatformAPI(object):

    def test_unauthorized_user(self, client, invalid_identity, authentication_headers,
                               organizations):
        resp = client.get(reverse('platform-list', args=[organizations[0].pk]),
                          **authentication_headers(invalid_identity))
        assert resp.status_code == 403

    def test_authorized_user_no_platforms_no_org(self, authenticated_client, organizations):
        resp = authenticated_client.get(reverse('platform-list', args=[organizations[0].pk]))
        assert resp.status_code == 404

    def test_authorized_user_no_platforms_org(self, authenticated_client, organizations,
                                              valid_identity):
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations[0])
        resp = authenticated_client.get(reverse('platform-list', args=[organizations[0].pk]))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_authorized_user_accessible_empty_platforms(self, authenticated_client, organizations,
                                                        valid_identity):
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations[0])
        resp = authenticated_client.get(reverse('platform-list', args=[organizations[0].pk]))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_authorized_user_inaccessible_platforms(self, authenticated_client, organizations,
                                                    platforms, valid_identity):
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations[0])
        resp = authenticated_client.get(reverse('platform-list', args=[organizations[0].pk]))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_authorized_user_accessible_platforms(self, authenticated_client, organizations,
                                                  platforms, valid_identity):
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations[0])
        OrganizationPlatform.objects.create(organization=organizations[0], platform=platforms[0])
        resp = authenticated_client.get(reverse('platform-list', args=[organizations[0].pk]))
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]['pk'] == platforms[0].pk

    def test_authorized_user_platforms_in_inaccessible_org(self, authenticated_client,
                                                           organizations, platforms):
        """
        There is an org and it has platforms, but the user cannot access the org
        """
        OrganizationPlatform.objects.create(organization=organizations[0], platform=platforms[0])
        resp = authenticated_client.get(reverse('platform-list', args=[organizations[0].pk]))
        assert resp.status_code == 404


@pytest.mark.django_db
class TestPlatformDetailedAPI(object):

    def test_unauthorized_user(self, client, invalid_identity, authentication_headers,
                               organizations):
        resp = client.get(reverse('detailed-platform-list', args=[organizations[0].pk]),
                          **authentication_headers(invalid_identity))
        assert resp.status_code == 403

    def test_authorized_user_no_platforms_no_org(self, authenticated_client, organizations):
        resp = authenticated_client.get(reverse('detailed-platform-list',
                                                args=[organizations[0].pk]))
        assert resp.status_code == 404

    def test_authorized_user_no_platforms_org(self, authenticated_client, organizations,
                                              valid_identity):
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations[0])
        resp = authenticated_client.get(reverse('detailed-platform-list',
                                                args=[organizations[0].pk]))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_authorized_user_accessible_empty_platforms(self, authenticated_client, organizations,
                                                        valid_identity):
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations[0])
        resp = authenticated_client.get(reverse('detailed-platform-list',
                                                args=[organizations[0].pk]))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_authorized_user_inaccessible_platforms(self, authenticated_client, organizations,
                                                    platforms, valid_identity):
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations[0])
        resp = authenticated_client.get(reverse('detailed-platform-list',
                                                args=[organizations[0].pk]))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_authorized_user_accessible_platforms(self, authenticated_client, organizations,
                                                  platforms, valid_identity):
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations[0])
        OrganizationPlatform.objects.create(organization=organizations[0], platform=platforms[0])
        resp = authenticated_client.get(reverse('detailed-platform-list',
                                                args=[organizations[0].pk]))
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]['pk'] == platforms[0].pk
        assert resp.json()[0]['title_count'] == 0
