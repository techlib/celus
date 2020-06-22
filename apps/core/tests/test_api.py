import pytest
from django.urls import reverse

from core.models import Identity, User


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


@pytest.mark.now
@pytest.mark.django_db
class TestAccountCreationAPI(object):
    def test_create_account(self, mailoutbox, client):
        """
        Tests that the API endpoint for account creation works as expected by the frontend code
        """
        assert User.objects.count() == 0
        assert len(mailoutbox) == 0
        resp = client.post(
            '/api/rest-auth/registration/',
            {'email': 'foo@bar.baz', 'password1': 'verysecret666', 'password2': 'verysecret666'},
        )
        assert resp.status_code == 201
        assert User.objects.count() == 1
        assert len(mailoutbox) == 1
        user = User.objects.get()
        assert user.email == 'foo@bar.baz'

    def test_create_account_bad_data(self, mailoutbox, client):
        """
        Tests that the API endpoint for account creation works as expected by the frontend code
        when there are problems with the data
        """
        assert User.objects.count() == 0
        assert len(mailoutbox) == 0
        resp = client.post(
            '/api/rest-auth/registration/',
            {'email': 'thisisnoemail', 'password1': 'verysecret666', 'password2': 'verysecret666'},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert 'email' in data
        assert User.objects.count() == 0
        assert len(mailoutbox) == 0
