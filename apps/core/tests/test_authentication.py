import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestAuthentication(object):

    def test_valid_identity_api_access(self, valid_identity, client):
        url = reverse('report-type-list')
        resp = client.get(url, HTTP_X_IDENTITY=valid_identity)
        assert resp.status_code == 200

    def test_valid_identity_api_access_using_authenticated_client_fixture(self,
                                                                          authenticated_client):
        url = reverse('report-type-list')
        resp = authenticated_client.get(url)
        assert resp.status_code == 200

    def test_invalid_identity_api_access(self, invalid_identity, client):
        url = reverse('report-type-list')
        resp = client.get(url, HTTP_X_IDENTITY=invalid_identity)
        assert resp.status_code == 403

    def test_no_identity_api_access(self, client):
        url = reverse('report-type-list')
        resp = client.get(url)
        assert resp.status_code == 403
