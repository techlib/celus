import pytest
from django.urls import reverse

from core.models import Identity


@pytest.mark.django_db
class TestUserAPI(object):

    def test_authenticated(self, authenticated_client):
        resp = authenticated_client.get(reverse('user_api_view'))
        assert resp.status_code == 200

    def test_unauthenticated(self, unauthenticated_client):
        resp = unauthenticated_client.get(reverse('user_api_view'))
        assert resp.status_code in (403, 401)  # depends on auth backend

    def test_authenticated_details(self, authenticated_client, valid_identity):
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        resp = authenticated_client.get(reverse('user_api_view'))
        assert resp.status_code == 200
        resp_data = resp.json()
        assert resp_data['username'] == identity.user.username
