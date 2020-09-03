import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestAuthentication:
    def test_valid_identity_api_access(self, valid_identity, client, authentication_headers):
        url = reverse('report-type-list')
        resp = client.get(url, **authentication_headers(valid_identity))
        assert resp.status_code == 200

    def test_valid_identity_api_access_using_authenticated_client_fixture(
        self, authenticated_client
    ):
        url = reverse('report-type-list')
        resp = authenticated_client.get(url)
        assert resp.status_code == 200

    def test_invalid_identity_api_access(self, invalid_identity, client, authentication_headers):
        url = reverse('report-type-list')
        resp = client.get(url, **authentication_headers(invalid_identity))
        assert resp.status_code in (403, 401)  # depends on auth backend

    def test_no_identity_api_access(self, client):
        url = reverse('report-type-list')
        resp = client.get(url)
        assert resp.status_code in (403, 401)  # depends on auth backend
