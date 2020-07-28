from unittest.mock import patch

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
        assert 'extra_data' in resp_data

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

    def test_send_email_verification(self, authenticated_client, valid_identity, mailoutbox, site):
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

    def test_set_extra_data(self, authenticated_client):
        """
        Checks that it is possible to store extra_data in User models
        """
        resp = authenticated_client.post(
            reverse('user_extra_data_view'), {'basic_tour_finished': True}
        )
        assert resp.status_code == 200
        user = authenticated_client.user
        user.refresh_from_db()
        assert 'basic_tour_finished' in user.extra_data
        assert user.extra_data['basic_tour_finished'] is True

    def test_set_extra_data_merging(self, authenticated_client):
        """
        Checks that when storing extra_data in User model, existing keys are not removed
        """
        user = authenticated_client.user
        user.extra_data['foobar'] = 10
        user.save()
        resp = authenticated_client.post(
            reverse('user_extra_data_view'), {'basic_tour_finished': True}
        )
        assert resp.status_code == 200
        user.refresh_from_db()
        assert 'basic_tour_finished' in user.extra_data
        assert user.extra_data['basic_tour_finished'] is True
        assert user.extra_data['foobar'] == 10

    def test_set_extra_data_bad_key(self, authenticated_client):
        """
        Checks that it is possible to store extra_data in User models, but only allowed ones.
        """
        resp = authenticated_client.post(reverse('user_extra_data_view'), {'foobarbaz': True})
        assert resp.status_code == 400
        user = authenticated_client.user
        user.refresh_from_db()
        assert 'foobarbaz' not in user.extra_data

    def test_set_extra_data_bad_value(self, authenticated_client):
        """
        Checks that value validation work for extra data
        """
        resp = authenticated_client.post(
            reverse('user_extra_data_view'), {'basic_tour_finished': 'foobarbaz'}
        )
        assert resp.status_code == 400

    def test_set_extra_data_no_data(self, authenticated_client):
        """
        Checks that posting empty data raises a BadRequest error
        """
        user = authenticated_client.user
        # add some extra data - we check later that it did not disappear
        user.extra_data['foobar'] = True
        old_extra_data = user.extra_data
        user.save()
        resp = authenticated_client.post(reverse('user_extra_data_view'), {})
        assert resp.status_code == 400
        user.refresh_from_db()
        assert 'foobar' in user.extra_data
        assert old_extra_data == user.extra_data


@pytest.mark.django_db
class TestAccountCreationAPI(object):
    test_user_data = {
        'email': 'foo@bar.baz',
        'password1': 'verysecret666',
        'password2': 'verysecret666',
    }

    def test_create_account(self, mailoutbox, client, site):
        """
        Tests that the API endpoint for account creation works as expected by the frontend code
        """
        assert User.objects.count() == 0
        assert len(mailoutbox) == 0
        with patch('core.signals.async_mail_admins'):  # fake celery task
            resp = client.post('/api/rest-auth/registration/', self.test_user_data)
        assert resp.status_code == 201
        assert User.objects.count() == 1
        assert len(mailoutbox) == 1
        user = User.objects.get()
        assert user.email == 'foo@bar.baz'
        assert user.email_verified is False
        assert user.email_verification["status"] == User.EMAIL_VERIFICATION_STATUS_PENDING
        assert user.emailaddress_set.count() == 1
        assert user.emailaddress_set.first().emailconfirmation_set.count() == 1

    def test_create_account_same_username(self, client, site):
        """
        Tests that is it possible to create two accounts with the same part before @ in email
        """
        assert User.objects.count() == 0
        with patch('core.signals.async_mail_admins'):  # fake celery task
            resp = client.post('/api/rest-auth/registration/', self.test_user_data)
        assert resp.status_code == 201
        assert User.objects.count() == 1
        second_user_data = dict(self.test_user_data)
        second_user_data['email'] = 'foo@baz.bar'
        with patch('core.signals.async_mail_admins'):  # fake celery task
            resp = client.post('/api/rest-auth/registration/', second_user_data)
        assert resp.status_code == 201
        assert User.objects.count() == 2

    def test_create_account_bad_data(self, mailoutbox, client):
        """
        Tests that the API endpoint for account creation works as expected by the frontend code
        when there are problems with the data
        """
        assert User.objects.count() == 0
        assert len(mailoutbox) == 0
        with patch('core.signals.async_mail_admins'):  # fake celery task
            resp = client.post(
                '/api/rest-auth/registration/',
                {
                    'email': 'thisisnoemail',
                    'password1': 'verysecret666',
                    'password2': 'verysecret666',
                },
            )
        assert resp.status_code == 400
        data = resp.json()
        assert 'email' in data
        assert User.objects.count() == 0
        assert len(mailoutbox) == 0

    def test_create_account_email_customization(self, mailoutbox, client, site):
        """
        Tests that the email verification email sent when creating an account uses our own
        text and not the one provided with allauth.
        """
        with patch('core.signals.async_mail_admins'):  # fake celery task
            resp = client.post(
                '/api/rest-auth/registration/',
                {
                    'email': 'foo@bar.baz',
                    'password1': 'verysecret666',
                    'password2': 'verysecret666',
                },
            )
        assert resp.status_code == 201
        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        assert 'Celus.one' in mail.subject, "Celus.one must be mentioned in the email body"
        assert 'Celus.one' in mail.body, "Celus.one must be mentioned in the email body"
        assert '/verify-email/?key=' in mail.body, "We use custom url endpoint, it should be there"

    def test_create_account_email_customization_resend(
        self, mailoutbox, authenticated_client, site
    ):
        """
        Tests that the email verification email sent when re-sending verification email has custom
        text and not the one provided with allauth.
        """
        user = authenticated_client.user
        user.email = 'foo@bar.baz'
        user.save()
        # create email address to get user into the 'unverified' status
        EmailAddress.objects.create(user=user, email=user.email)
        resp = authenticated_client.post('/api/user/verify-email')
        assert resp.status_code == 200
        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        assert 'Celus.one' in mail.subject, "Celus.one must be mentioned in the email body"
        assert 'Celus.one' in mail.body, "Celus.one must be mentioned in the email body"
        assert '/verify-email/?key=' in mail.body, "We use custom url endpoint, it should be there"

    def test_email_admins_about_create_account(self, mailoutbox, client, site):
        """
        Tests that admins are sent a email when user creates an account
        """
        assert User.objects.count() == 0
        assert len(mailoutbox) == 0
        with patch('core.signals.async_mail_admins') as email_task:
            resp = client.post('/api/rest-auth/registration/', self.test_user_data)
            assert resp.status_code == 201
            assert User.objects.count() == 1
            assert email_task.delay.called, 'email to admins should be sent'


@pytest.mark.django_db
class TestBasicInfoAPI(object):
    def test_system_info_api_view(self, client, settings):
        resp = client.get(reverse('system_info_api_view'))
        assert resp.status_code == 200
        data = resp.json()
        # just a few hard-coded text values
        assert 'ALLOW_EMAIL_LOGIN' in data
        assert 'ALLOW_USER_REGISTRATION' in data
        # test it all
        for key in settings.EXPORTED_SETTINGS:
            assert key in data
