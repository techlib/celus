import pytest

from datetime import datetime

from allauth.account.models import EmailAddress, EmailConfirmation
from django.urls import reverse
from django.utils import timezone

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

    def test_verified_email(self, authenticated_client, valid_identity):
        """
        Test which checks email validity status
        """
        user = authenticated_client.user
        sent_time = datetime(2020, 1, 1, tzinfo=timezone.utc)

        def get_response() -> dict:
            resp = authenticated_client.get(reverse('user_api_view'))
            assert resp.status_code == 200
            return resp.json()

        resp_data = get_response()

        assert resp_data["email_verification_status"] == User.EMAIL_VERIFICATION_STATUS_UNKNOWN
        assert resp_data["email_verification_sent"] is None
        assert User.objects.get(pk=user.pk).email_verified is False

        # Create linked email
        # Situation when the verification email was not sent
        email_address = EmailAddress.objects.create(user=user, email=user.email)

        resp_data = get_response()

        assert resp_data["email_verification_status"] == User.EMAIL_VERIFICATION_STATUS_PENDING
        assert resp_data["email_verification_sent"] is None
        assert User.objects.get(pk=user.pk).email_verified is False

        # Create confirmation
        confirmation = EmailConfirmation.objects.create(email_address=email_address)
        confirmation.sent = sent_time
        confirmation.save()

        resp_data = get_response()

        assert resp_data["email_verification_status"] == User.EMAIL_VERIFICATION_STATUS_PENDING
        assert resp_data["email_verification_sent"] == sent_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        assert User.objects.get(pk=user.pk).email_verified is False

        # Make the email verified
        email_address.verified = True
        email_address.save()

        resp_data = get_response()

        assert resp_data["email_verification_status"] == User.EMAIL_VERIFICATION_STATUS_VERIFIED
        assert resp_data["email_verification_sent"] == sent_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        assert User.objects.get(pk=user.pk).email_verified is True

    def test_send_email_verification(self, authenticated_client, valid_identity, mailoutbox):
        user = authenticated_client.user
        user.email = valid_identity
        user.save()

        # get user info
        resp = authenticated_client.get(reverse('user_api_view'))
        assert resp.status_code == 200
        resp_data = resp.json()
        assert resp_data["email_verification_status"] == User.EMAIL_VERIFICATION_STATUS_UNKNOWN
        assert resp_data["email_verification_sent"] is None
        assert User.objects.get(pk=user.pk).email_verified is False
        assert len(mailoutbox) == 0

        # send verification email
        resp = authenticated_client.post(reverse('user_api_verify_email_view'))
        assert resp.status_code == 200
        resp_data = resp.json()
        assert resp_data["status"] == User.EMAIL_VERIFICATION_STATUS_PENDING
        assert resp_data["email_sent"] is not None
        assert len(mailoutbox) == 1

        # obtain user info again
        resp = authenticated_client.get(reverse('user_api_view'))
        assert resp.status_code == 200
        resp_data = resp.json()

        assert resp_data["email_verification_status"] == User.EMAIL_VERIFICATION_STATUS_PENDING
        assert resp_data["email_verification_sent"] is not None


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
        assert user.email_verified is False
        assert user.email_verification["status"] == User.EMAIL_VERIFICATION_STATUS_PENDING
        assert user.emailaddress_set.count() == 1
        assert user.emailaddress_set.first().emailconfirmation_set.count() == 1

        # check

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
