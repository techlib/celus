import hmac
import re
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from allauth.account.models import EmailAddress, EmailConfirmation
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.core.files.base import ContentFile
from django.urls import reverse
from freezegun import freeze_time

from core.fake_data import UserFactory
from core.models import User
from test_scenarios.basic import (
    basic1,  # noqa
    clients,  # noqa
    data_sources,  # noqa
    identities,  # noqa
    organizations,  # noqa
    otp_devices,  # noqa
    platforms,  # noqa
    users,  # noqa
)


@pytest.fixture
def disallow_eduid_login(settings):
    settings.ALLOW_EDUID_LOGIN = False
    settings.AUTHENTICATION_BACKENDS = [
        e
        for e in settings.AUTHENTICATION_BACKENDS
        if e != "apps.core.auth.EDUIdAuthenticationBackend"
    ]


@pytest.mark.django_db
class TestUserAPI:
    def test_authenticated(self, clients):
        resp = clients["user1"].get(reverse("user_api_view"))
        assert resp.status_code == 200

    def test_unauthenticated(self, clients):
        resp = clients["unauthenticated"].get(reverse("user_api_view"))
        assert resp.status_code in (403, 401)  # depends on auth backend

    def test_authenticated_details(self, clients, users):
        resp = clients["user1"].get(reverse("user_api_view"))
        assert resp.status_code == 200
        resp_data = resp.json()
        assert resp_data["username"] == users["user1"].username
        assert "extra_data" in resp_data

    def test_user_language(self, clients, users):
        users["user1"].language = "cs"
        users["user1"].save()
        resp = clients["user1"].put(reverse("user_lang_api_view"), {"language": "en"})
        assert resp.status_code == 200
        users["user1"].refresh_from_db()
        assert users["user1"].language == "en"

    def test_user_language_with_otp_device(
        self, settings, clients, users, otp_devices, disallow_eduid_login
    ):
        settings.OTP_ENABLED = True
        users["user1"].language = "cs"
        users["user1"].save()
        resp = clients["user1"].put(reverse("user_lang_api_view"), {"language": "en"})
        assert resp.status_code == 403, "Missing device verification"

        # Skip 2fa
        users["user1"].skip_2fa = True
        users["user1"].save()
        resp = clients["user1"].put(reverse("user_lang_api_view"), {"language": "en"})
        assert resp.status_code == 200, "2FA skipped per user"

        # Restore state and rerun
        users["user1"].language = "cs"
        users["user1"].skip_2fa = False
        users["user1"].save()
        resp = clients["user1"].put(reverse("user_lang_api_view"), {"language": "en"})
        assert resp.status_code == 403, "Missing device verification (unskipped)"

        # Send verification email
        resp = clients["user1"].post(reverse("otp-generate", args=(otp_devices["user1"].pk,)))
        assert resp.status_code == 200

        # Verify code
        otp_devices["user1"].refresh_from_db()
        resp = clients["user1"].post(
            reverse("otp-verify", args=(otp_devices["user1"].pk,)),
            {"code": otp_devices["user1"].token},
        )
        assert resp.status_code == 200, "code verified and cookie set"

        resp = clients["user1"].put(reverse("user_lang_api_view"), {"language": "en"})
        assert resp.status_code == 200, "Allow to change language when 2FA is done"

    def test_user_language_with_unlinked_otp_device_notification_mail(
        self, settings, clients, users, disallow_eduid_login, mailoutbox
    ):
        settings.OTP_ENABLED = True
        with freeze_time("2024-01-01 00:00:00"):
            with patch("core.tasks.async_mail_admins") as email_task:
                resp = clients["user1"].put(reverse("user_lang_api_view"), {"language": "en"})
                assert resp.status_code == 200
                assert email_task.delay.called, "Notification email sent"

        with freeze_time("2024-01-01 01:00:00"):
            with patch("core.tasks.async_mail_admins") as email_task:
                resp = clients["user1"].put(reverse("user_lang_api_view"), {"language": "en"})
                assert resp.status_code == 200
                assert not email_task.delay.called, "Notification email not sent - still in timeout"

        with freeze_time("2024-01-05 00:00:00"):
            with patch("core.tasks.async_mail_admins") as email_task:
                resp = clients["user1"].put(reverse("user_lang_api_view"), {"language": "en"})
                assert resp.status_code == 200
                assert email_task.delay.called, "Notification email sent - timeout expired"

    def test_verified_email(self, settings, users, clients, disallow_eduid_login):
        """
        Test which checks email validity status
        """
        user = users["user1"]
        sent_time = datetime(2020, 1, 1, tzinfo=timezone.utc)

        def get_response() -> dict:
            resp = clients["user1"].get(reverse("user_api_view"))
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
        assert resp_data["email_verification_sent"] == sent_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        assert User.objects.get(pk=user.pk).email_verified is False

        # Make the email verified
        email_address.verified = True
        email_address.save()

        resp_data = get_response()

        assert resp_data["email_verification_status"] == User.EMAIL_VERIFICATION_STATUS_VERIFIED
        assert resp_data["email_verification_sent"] == sent_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        assert User.objects.get(pk=user.pk).email_verified is True

    def test_send_email_verification(
        self, mailoutbox, site, settings, users, clients, disallow_eduid_login
    ):
        user = users["user1"]

        # get user info
        resp = clients["user1"].get(reverse("user_api_view"))
        assert resp.status_code == 200
        resp_data = resp.json()
        assert resp_data["email_verification_status"] == User.EMAIL_VERIFICATION_STATUS_UNKNOWN
        assert resp_data["email_verification_sent"] is None
        assert User.objects.get(pk=user.pk).email_verified is False
        assert len(mailoutbox) == 0

        # send verification email
        resp = clients["user1"].post(reverse("user_api_verify_email_view"))
        assert resp.status_code == 200
        resp_data = resp.json()
        assert resp_data["status"] == User.EMAIL_VERIFICATION_STATUS_PENDING
        assert resp_data["email_sent"] is not None
        assert len(mailoutbox) == 1

        # obtain user info again
        resp = clients["user1"].get(reverse("user_api_view"))
        assert resp.status_code == 200
        resp_data = resp.json()

        assert resp_data["email_verification_status"] == User.EMAIL_VERIFICATION_STATUS_PENDING
        assert resp_data["email_verification_sent"] is not None

    @pytest.mark.parametrize(
        ["key", "value"],
        [
            ("basic_tour_finished", True),
            ("fiscal_year_start_month", 4),
            ("last_dismissed_release", "5.2.1"),
            ("last_seen_release", "5.2.1"),
        ],
    )
    def test_set_extra_data(self, clients, users, key, value):
        """
        Checks that it is possible to store extra_data in User models
        """
        resp = clients["user1"].post(reverse("user_extra_data_view"), {key: value})
        assert resp.status_code == 200
        user = users["user1"]
        user.refresh_from_db()
        assert user.extra_data[key] == value

    def test_set_extra_data_merging(self, clients, users):
        """
        Checks that when storing extra_data in User model, existing keys are not removed
        """
        user = users["user1"]
        user.extra_data["foobar"] = 10
        user.save()
        resp = clients["user1"].post(reverse("user_extra_data_view"), {"basic_tour_finished": True})
        assert resp.status_code == 200
        user.refresh_from_db()
        assert "basic_tour_finished" in user.extra_data
        assert user.extra_data["basic_tour_finished"] is True
        assert user.extra_data["foobar"] == 10

    def test_set_extra_data_bad_key(self, clients, users):
        """
        Checks that it is possible to store extra_data in User models, but only allowed ones.
        """
        resp = clients["user1"].post(reverse("user_extra_data_view"), {"foobarbaz": True})
        assert resp.status_code == 400
        user = users["user1"]
        user.refresh_from_db()
        assert "foobarbaz" not in user.extra_data

    def test_set_extra_data_bad_value(self, clients):
        """
        Checks that value validation work for extra data
        """
        resp = clients["user1"].post(
            reverse("user_extra_data_view"), {"basic_tour_finished": "foobarbaz"}
        )
        assert resp.status_code == 400

    def test_set_extra_data_no_data(self, clients, users):
        """
        Checks that posting empty data raises a BadRequest error
        """
        user = users["user1"]
        # add some extra data - we check later that it did not disappear
        user.extra_data["foobar"] = True
        old_extra_data = user.extra_data
        user.save()
        resp = clients["user1"].post(reverse("user_extra_data_view"), {})
        assert resp.status_code == 400
        user.refresh_from_db()
        assert "foobar" in user.extra_data
        assert old_extra_data == user.extra_data

    @pytest.mark.parametrize(
        "otp_enabled,skip_2fa,required",
        ((True, True, False), (True, False, True), (False, True, False), (False, False, False)),
    )
    def test_otp_required(
        self, otp_enabled, skip_2fa, required, settings, clients, users, otp_devices
    ):
        settings.OTP_ENABLED = otp_enabled
        users["master_user"].skip_2fa = skip_2fa
        users["master_user"].save()
        resp = clients["master_user"].get(reverse("user_api_view"))
        assert resp.status_code == 200
        if required:
            assert len(resp.data["otp_required"]) == 1
        else:
            assert not resp.data["otp_required"]


@pytest.mark.django_db
class TestAccountCreationAPI:
    test_user_data = {
        "email": "foo@bar.baz",
        "password1": "verysecret666",
        "password2": "verysecret666",
    }

    def test_create_account(self, mailoutbox, clients, site, settings, disallow_eduid_login):
        """
        Tests that the API endpoint for account creation works as expected by the frontend code
        """
        User.objects.all().delete()
        assert User.objects.count() == 0
        assert len(mailoutbox) == 0
        with patch("core.signals.async_mail_customer_care_admins"):  # fake celery task
            resp = clients["unauthenticated"].post(
                "/api/rest-auth/registration/", self.test_user_data
            )
        assert resp.status_code == 201
        assert User.objects.count() == 1
        assert len(mailoutbox) == 1
        user = User.objects.get()
        assert user.email == "foo@bar.baz"
        assert user.email_verified is False
        assert user.email_verification["status"] == User.EMAIL_VERIFICATION_STATUS_PENDING
        assert user.emailaddress_set.count() == 1
        assert user.emailaddress_set.first().emailconfirmation_set.count() == 1

    def test_create_account_same_username(self, clients, site):
        """
        Tests that is it possible to create two accounts with the same part before @ in email
        """
        User.objects.all().delete()
        assert User.objects.count() == 0
        with patch("core.signals.async_mail_customer_care_admins"):  # fake celery task
            resp = clients["unauthenticated"].post(
                "/api/rest-auth/registration/", self.test_user_data
            )
        assert resp.status_code == 201
        assert User.objects.count() == 1
        second_user_data = dict(self.test_user_data)
        second_user_data["email"] = "foo@baz.bar"
        with patch("core.signals.async_mail_customer_care_admins"):  # fake celery task
            resp = clients["unauthenticated"].post("/api/rest-auth/registration/", second_user_data)
        assert resp.status_code == 201
        assert User.objects.count() == 2

    @pytest.mark.parametrize("first_verified", [True, False])
    @pytest.mark.parametrize("case_mismatch", [True, False])
    def test_create_account_same_email(self, client, first_verified, case_mismatch):
        """
        Tests that it is not possible to create two accounts with the same email
        - regardless if the email is verified (changed at the end of 2024)
        """
        user = UserFactory.create(email="foo@bar.baz")
        EmailAddress.objects.create(user=user, email=user.email, verified=first_verified)
        with patch("core.signals.async_mail_customer_care_admins") as mail_task:  # fake celery task
            resp = client.post(
                "/api/rest-auth/registration/",
                {
                    "email": "foo@bar.baz" if not case_mismatch else "Foo@bar.baz",
                    "password1": "verysecret666",
                    "password2": "verysecret666",
                },
            )
            assert resp.status_code == 400
            assert not mail_task.called

    @pytest.mark.parametrize("lowercase_email", [True, False])
    def test_created_user_has_lowercase_email(self, client, lowercase_email):
        """
        Tests that the email address of the created user is always lowercased
        """
        with patch("core.signals.async_mail_customer_care_admins"):  # fake celery task
            resp = client.post(
                "/api/rest-auth/registration/",
                {
                    "email": "foo@bar.baz" if lowercase_email else "Foo@BAR.baz",
                    "password1": "verysecret666",
                    "password2": "verysecret666",
                },
            )
        assert resp.status_code == 201
        assert User.objects.count() == 1
        user = User.objects.get()
        assert user.email == "foo@bar.baz"
        assert user.emailaddress_set.count() == 1
        assert user.emailaddress_set.first().email == "foo@bar.baz"

    def test_create_account_bad_data(self, mailoutbox, clients):
        """
        Tests that the API endpoint for account creation works as expected by the frontend code
        when there are problems with the data
        """
        User.objects.all().delete()
        assert User.objects.count() == 0
        assert len(mailoutbox) == 0
        with patch("core.signals.async_mail_customer_care_admins"):  # fake celery task
            resp = clients["unauthenticated"].post(
                "/api/rest-auth/registration/",
                {
                    "email": "thisisnoemail",
                    "password1": "verysecret666",
                    "password2": "verysecret666",
                },
            )
        assert resp.status_code == 400
        data = resp.json()
        assert "email" in data
        assert User.objects.count() == 0
        assert len(mailoutbox) == 0

    def test_create_account_email_customization(self, mailoutbox, clients, site):
        """
        Tests that the email verification email sent when creating an account uses our own
        text and not the one provided with allauth.
        """
        with patch("core.signals.async_mail_customer_care_admins"):  # fake celery task
            resp = clients["unauthenticated"].post(
                "/api/rest-auth/registration/",
                {
                    "email": "foo@bar.baz",
                    "password1": "verysecret666",
                    "password2": "verysecret666",
                },
            )
        assert resp.status_code == 201
        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        assert "CELUS" in mail.subject, "CELUS must be mentioned in the email body"
        assert "CELUS" in mail.body, "CELUS must be mentioned in the email body"
        assert "/verify-email/?key=" in mail.body, "We use custom url endpoint, it should be there"

    @pytest.mark.parametrize("logged_for_verification", [True, False])
    def test_create_account_email_customization_resend(
        self,
        mailoutbox,
        users,
        site,
        clients,
        otp_devices,
        disallow_eduid_login,
        logged_for_verification,
        client,
        settings,
    ):
        """
        Tests that the email verification email sent when re-sending verification email has custom
        text and not the one provided with allauth.
        """
        settings.OTP_ENABLED = True
        # make email address unverified
        email_address = EmailAddress.objects.get(user=users["user1"])
        email_address.verified = False
        email_address.save()

        resp = clients["user1"].post("/api/user/verify-email")
        assert resp.status_code == 200
        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        assert "CELUS" in mail.subject, "CELUS must be mentioned in the email body"
        assert "CELUS" in mail.body, "CELUS must be mentioned in the email body"
        assert "/verify-email/?key=" in mail.body, "We use custom url endpoint, it should be there"

        # the user may or may not be logged in when he does the verification
        c = clients["user1"] if logged_for_verification else client
        resp = c.post(
            reverse("user_verify_email_code"),
            {"key": email_address.emailconfirmation_set.all().last().key},
        )
        assert resp.status_code == 200
        assert resp.cookies.get(f"otp_device_id_{users['user1'].pk}") is not None, (
            "device cookie is set"
        )
        user1 = User.objects.get(pk=users["user1"].pk)
        assert user1.email_verified

    def test_email_admins_about_create_account(self, clients, site):
        """
        Tests that admins are sent an email when user creates an account
        """
        User.objects.all().delete()
        assert User.objects.count() == 0
        with patch("core.signals.async_mail_customer_care_admins") as email_task:
            resp = clients["unauthenticated"].post(
                "/api/rest-auth/registration/", self.test_user_data
            )
            assert resp.status_code == 201
            assert User.objects.count() == 1
            assert email_task.delay.called, "email to admins should be sent"


@pytest.mark.django_db
class TestBasicInfoAPI:
    def test_system_info_api_view(self, clients, settings):
        resp = clients["unauthenticated"].get(reverse("system_info_api_view"))
        assert resp.status_code == 200
        data = resp.json()
        # just a few hard-coded text values
        assert "ALLOW_EMAIL_LOGIN" in data
        assert "ALLOW_USER_REGISTRATION" in data
        # test it all
        for key in settings.EXPORTED_SETTINGS:
            assert key in data


@pytest.mark.django_db
class TestInvitationAndPasswordResetAPI:
    def test_password_reset_email_is_sent(self, clients, users, mailoutbox):
        """
        Test that the API endpoint for sending password reset emails works and really sends out
        an email with the correct link
        """
        assert len(mailoutbox) == 0
        resp = clients["unauthenticated"].post(
            "/api/rest-auth/password/reset/", {"email": users["user1"].email}
        )
        assert resp.status_code == 200
        assert len(mailoutbox) == 1
        assert "/reset-password/?" in mailoutbox[0].body, "reset link should be present in mail"

    def test_password_reset_confirm_endpoint_works(self, clients, users, mailoutbox):
        """
        Test that password can be changed using the link sent when password reset it triggered
        """
        # at first we need to get the appropriate input for the endpoint
        # the code is buried in a django form, so we simply simulate sending the email and
        # get the data from there
        resp = clients["unauthenticated"].post(
            "/api/rest-auth/password/reset/", {"email": users["user1"].email}
        )
        assert resp.status_code == 200
        assert len(mailoutbox) == 1
        # extract uid and token to use for the endpoint
        # - the link itself points to frontend so it is not directly usable
        uid = re.search(r"\?uid=(\w+)&", mailoutbox[0].body).group(1)
        token = re.search(r"&token=([\w-]+)", mailoutbox[0].body).group(1)
        assert uid and token, "both uid and token must be present in the email body"
        # now try resetting the password
        old_pwd = users["user1"].password
        new_pwd = "4aKVkhMfVP"
        resp = clients["unauthenticated"].post(
            "/api/user/password-reset",
            {"uid": uid, "token": token, "new_password1": new_pwd, "new_password2": new_pwd},
        )
        assert resp.status_code == 200
        assert len(mailoutbox) == 1, "no new email after password reset"
        users["user1"].refresh_from_db()
        assert users["user1"].password != old_pwd
        # one more thing - check that the user email is thus verified
        assert users["user1"].email_verified

    def test_invitation_workflow_works(self, admin_client, client, mailoutbox, settings, site):
        """
        Test that password can be changed using the link sent when inviting users
        """
        settings.ALLOWED_HOSTS = ["testserver", site.domain]
        user = User.objects.create(username="foo", email="foo@bar.baz")
        # invitation is sent using an admin action
        resp = admin_client.post(
            reverse("admin:core_user_changelist"),
            {"action": "send_invitation_emails", ACTION_CHECKBOX_NAME: [user.pk]},
        )
        assert resp.status_code == 302
        assert len(mailoutbox) == 1
        # extract uid and token to use for the endpoint
        # - the link itself points to frontend so it is not directly usable
        uid = re.search(r"\?uid=(\w+)&", mailoutbox[0].body).group(1)
        token = re.search(r"&token=([\w-]+)", mailoutbox[0].body).group(1)
        assert uid and token, "both uid and token must be present in the email body"
        # now try resetting the password
        old_pwd = user.password
        new_pwd = "4aKVkhMfVP"
        resp = client.post(
            "/api/user/password-reset",
            {"uid": uid, "token": token, "new_password1": new_pwd, "new_password2": new_pwd},
        )
        assert resp.status_code == 200
        assert len(mailoutbox) == 1, "no new email after password reset"
        user.refresh_from_db()
        assert user.password != old_pwd
        # one more thing - check that the user email is thus verified
        assert user.email_verified

    def test_invitation_workflow_works_with_eduid(
        self, admin_client, client, mailoutbox, settings, site
    ):
        """
        Test that password can be changed using the link sent when inviting users
        """
        settings.ALLOWED_HOSTS = ["testserver", site.domain]
        settings.ALLOW_EDUID_LOGIN = True
        settings.ALLOW_EMAIL_LOGIN = False
        user = User.objects.create(username="foo", email="foo@bar.baz")
        # invitation is sent using an admin action
        resp = admin_client.post(
            reverse("admin:core_user_changelist"),
            {"action": "send_invitation_emails", ACTION_CHECKBOX_NAME: [user.pk]},
        )
        assert resp.status_code == 302
        assert len(mailoutbox) == 1
        # extract uid and token to use for the endpoint
        # - the link itself points to frontend so it is not directly usable
        uid = re.search(r"\?uid=(\w+)&", mailoutbox[0].body).group(1)
        token = re.search(r"&token=([\w-]+)", mailoutbox[0].body).group(1)
        assert uid and token, "both uid and token must be present in the email body"
        # now try resetting the password
        resp = client.post(
            reverse("confirm_identity"),
            {"uid": uid, "token": token},
            headers={"HTTP_X_MAIL": "foo@bar.baz", "X_IDENTITY": "foo@bar-baz.id"},
        )
        assert resp.status_code == 200
        assert len(mailoutbox) == 1, "no new email after password reset"
        user.refresh_from_db()
        assert user.email_verified
        assert user.identity_set.count() == 1
        assert user.identity_set.first().identity == "foo@bar-baz.id"
        # try it one more time to confirm that the link is one-time only
        resp = client.post(
            reverse("confirm_identity"),
            {"uid": uid, "token": token},
            headers={"HTTP_X_MAIL": "foo@bar.baz", "X_IDENTITY": "bar@bar-baz.id"},
        )
        assert resp.status_code == 400
        assert user.identity_set.count() == 1
        assert user.identity_set.first().identity == "foo@bar-baz.id", "identity should not change"

    @pytest.mark.parametrize(
        ["site_domain", "allowed_hosts", "ok"],
        [
            ("foo.celus.net", ["foo.celus.net"], True),
            ("bar.celus.net", ["foo.celus.net"], False),
            ("foo.celus.net", ["*"], False),
            ("*", ["foo.celus.net"], False),
            ("*.celus.net", ["foo.celus.net"], False),
        ],
    )
    def test_invitation_sending_checks(
        self, admin_client, admin_user, settings, mailoutbox, site_domain, allowed_hosts, ok, site
    ):
        """
        Test that the code for preventing sending invitations with incorrect domain name works
        """
        # prepare the site
        site.domain = site_domain
        site.save()
        # and settings
        settings.ALLOWED_HOSTS = ["testserver", *allowed_hosts]
        resp = admin_client.post(
            reverse("admin:core_user_changelist"),
            {"action": "send_invitation_emails", ACTION_CHECKBOX_NAME: [admin_user.pk]},
        )
        assert resp.status_code == 302
        if ok:
            assert len(mailoutbox) == 1, "invitation was sent"
        else:
            assert len(mailoutbox) == 0, "invitation was not sent"


@pytest.mark.django_db
class TestMiddleware:
    @pytest.mark.parametrize(
        "same_version,status",
        (
            (None, 200),  # Client doesn't return celus version
            (True, 200),  # Client celus version == server celus version
            (False, 409),  # Client celus version != celus server version
        ),
    )
    def test_version(self, clients, same_version, status, settings):
        if same_version is None:
            resp = clients["user1"].get(reverse("user_api_view"))
        else:
            resp = clients["user1"].get(
                reverse("user_api_view"),
                HTTP_CELUS_VERSION=settings.CELUS_VERSION if same_version else "0.0.0",
            )

        assert resp.status_code == status
        assert resp.has_header("CELUS-VERSION")
        assert re.match(r"^[0-9]+\.[0-9]+\.[0-9]+[0-9A-Za-z-]*$", resp["CELUS-VERSION"]), (
            "Version follows semantic versioning"
        )

        assert resp["CELUS-VERSION"] == settings.CELUS_VERSION


@pytest.mark.django_db
class TestUserExistsView:
    @pytest.mark.parametrize("exists", [True, False])
    def test_user_exists(self, clients, exists, settings):
        settings.OCTOPUS_HMAC_KEY = "testtesttesttest"
        email = "foo@bar.baz"
        check = hmac.digest(
            settings.OCTOPUS_HMAC_KEY.encode("utf-8"),
            email.encode("utf-8"),
            settings.OCTOPUS_HMAC_ALGO,
        ).hex()
        if exists:
            UserFactory.create(email=email)
        resp = clients["unauthenticated"].get(reverse("user_exists_api_view"), {"hmac": check})
        assert resp.status_code == 200
        assert resp.json() == {"exists": exists}

    @pytest.mark.parametrize(
        "check",
        [
            "foo",
            "alfkjasdlkfjsdl",
            "83db689eb6947d8becd6364b523f1aef87a889a1",
            "83db689eb6947d8becd6364b523f/aef87a889a1",
            "3b4bb87b4b06f185bd3fba4203e5e44b52279adab79c3f6dc33f4c44dd11b5a8",
            "3b4bb87b4b06f185bd3fba4203e5e44b52279adab79c3f6dc33f%c44dd11b5a8",
        ],
    )
    def test_user_exists_fuzzy(self, clients, settings, check):
        settings.OCTOPUS_HMAC_KEY = "testtesttesttest"
        resp = clients["unauthenticated"].get(reverse("user_exists_api_view"), {"hmac": check})
        assert resp.status_code == 200

    @pytest.mark.parametrize(
        ["in_db", "in_hmac", "exists"],
        [
            ("foo@bar.baz", "foo@bar.baz", True),
            ("bar@baz.foo", "foo@bar.baz", False),
            ("Foo@bar.baz", "foo@bar.baz", True),
            ("FOO@BAR.BaZ ", "foo@bar.baz", True),
        ],
    )
    def test_user_exists_with_normalization(self, client, exists, settings, in_db, in_hmac):
        settings.OCTOPUS_HMAC_KEY = "testtesttesttest"
        check = hmac.digest(
            settings.OCTOPUS_HMAC_KEY.encode("utf-8"),
            in_hmac.encode("utf-8"),
            settings.OCTOPUS_HMAC_ALGO,
        ).hex()
        UserFactory.create(email=in_db)
        resp = client.get(reverse("user_exists_api_view"), {"hmac": check})
        assert resp.status_code == 200
        assert resp.json() == {"exists": exists}


@pytest.mark.django_db
class TestManagementCommandAPI:
    def test_list_commands(self, clients, settings):
        settings.EXPOSED_MANAGEMENT_COMMANDS = [("organizations", "load_sushi_credentials")]
        resp = clients["su"].get(reverse("management-command-list"))
        assert resp.status_code == 200
        assert resp.json() == [
            {
                "name": "load_sushi_credentials",
                "help": "Load SUSHI credentials from a CSV file",
                "args": [
                    {
                        "name": "file",
                        "type": "file",
                        "required": False,
                        "default": None,
                        "metavar": None,
                        "help": "CSV file to import",
                    },
                    {
                        "name": "knowledgebase_urls",
                        "type": "bool",
                        "required": False,
                        "default": False,
                        "metavar": None,
                        "help": "If available, use knowledgebase urls instead of the ones stored "
                        "in the file",
                    },
                    {
                        "name": "override_org",
                        "default": None,
                        "required": False,
                        "metavar": "_ORG_ID_",
                        "type": "str",
                        "help": "pk, name_en or short_name_en of the organization for "
                        "which you intend to import credentials",
                    },
                ],
                "uses_doit": True,
            }
        ]

    @pytest.mark.parametrize(
        ["user_type", "has_access"],
        [
            ["no_user", False],
            ["invalid", False],
            ["unrelated", False],
            ["related_user", False],
            ["related_admin", False],
            ["master_user", False],
            ["superuser", True],
        ],
    )
    def test_list_commands_access(self, settings, user_type, has_access, client_by_user_type):
        settings.EXPOSED_MANAGEMENT_COMMANDS = [("core", "echo")]
        client, _ = client_by_user_type(user_type)
        resp = client.get(reverse("management-command-list"))
        if has_access:
            assert resp.status_code == 200
        else:
            assert resp.status_code in (403, 401)

    def test_list_commands_echo(self, admin_client, settings):
        settings.EXPOSED_MANAGEMENT_COMMANDS = [("core", "echo")]
        resp = admin_client.get(reverse("management-command-list"))
        assert resp.status_code == 200
        assert resp.json() == [
            {
                "name": "echo",
                "help": "Echo the given string to stdout or stderr",
                "args": [
                    {
                        "name": "echo",
                        "type": "str",
                        "required": True,
                        "default": None,
                        "metavar": None,
                        "help": "String to be returned back",
                    },
                    {
                        "name": "error",
                        "type": "bool",
                        "required": False,
                        "default": False,
                        "metavar": None,
                        "help": "When given, echo will be printed to stderr instead of stdout",
                    },
                    {
                        "name": "file",
                        "type": "file",
                        "required": False,
                        "default": None,
                        "metavar": "foobar",
                        "help": "When given, the contents of the file will be echoed instead "
                        "of the string",
                    },
                ],
                "uses_doit": True,
            }
        ]

    def test_list_commands_incorrect_config(self, admin_client, settings):
        settings.EXPOSED_MANAGEMENT_COMMANDS = [("core", "foo")]
        resp = admin_client.get(reverse("management-command-list"))
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.parametrize("stderr", [True, False])
    @pytest.mark.parametrize("doit", [True, False])
    def test_run_command_echo(self, admin_client, settings, stderr, doit):
        settings.EXPOSED_MANAGEMENT_COMMANDS = [("core", "echo")]
        resp = admin_client.post(
            reverse("management-command-run", args=["echo"]),
            {"echo": "foo", "error": stderr, "doit": doit},
        )
        assert resp.status_code == 200
        common = {
            "log": "INFO:: Starting echo command\n",
            "exception": None if doit else "not doing it",
        }
        if stderr:
            assert resp.json() == {"stdout": "", "stderr": "foo\n", **common}
        else:
            assert resp.json() == {"stdout": "foo\n", "stderr": "", **common}

    @pytest.mark.parametrize("doit", [True, False])
    def test_run_command_echo_with_file(self, admin_client, settings, doit):
        settings.EXPOSED_MANAGEMENT_COMMANDS = [("core", "echo")]
        cf = ContentFile(b"foobar")
        resp = admin_client.post(
            reverse("management-command-run", args=["echo"]),
            {"echo": "baz", "error": True, "file": cf, "doit": doit},
        )
        assert resp.status_code == 200
        assert resp.json() == {
            "stdout": "",
            "stderr": "foobar\n",
            "log": "INFO:: Starting echo command\n",
            "exception": None if doit else "not doing it",
        }

    @pytest.mark.parametrize(
        ["user_type", "has_access"],
        [
            ["no_user", False],
            ["invalid", False],
            ["unrelated", False],
            ["related_user", False],
            ["related_admin", False],
            ["master_user", False],
            ["superuser", True],
        ],
    )
    def test_run_command_access(self, settings, user_type, has_access, client_by_user_type):
        settings.EXPOSED_MANAGEMENT_COMMANDS = [("core", "echo")]
        client, _ = client_by_user_type(user_type)
        resp = client.post(reverse("management-command-run", args=["echo"]))
        if has_access:
            assert resp.status_code == 200
        else:
            assert resp.status_code in (403, 401)


@pytest.mark.django_db
class TestOtpAPI:
    def test_list(self, settings, clients, users, otp_devices):
        settings.OTP_ENABLED = True
        resp = clients["master_user"].get(reverse("otp-list"))
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_create(self, settings, clients, users, otp_devices):
        settings.OTP_ENABLED = True
        resp = clients["master_user"].post(reverse("otp-list"), {"name": "default"})
        assert resp.status_code == 201
        assert resp.data["name"] == "default"
        assert resp.data["email"] is None
        assert resp.cookies.get(f"otp_device_id_{users['master_user'].pk}") is not None, (
            "device cookie is set"
        )

    def test_create_email_not_verified(
        self, settings, clients, users, otp_devices, disallow_eduid_login
    ):
        settings.OTP_ENABLED = True
        EmailAddress.objects.all().delete()
        resp = clients["master_user"].post(reverse("otp-list"), {"name": "default"})
        assert resp.status_code == 400
        assert "user" in resp.data

    def test_destroy(self, settings, clients, users, otp_devices, basic1):
        settings.OTP_ENABLED = True

        resp = clients["admin2"].delete(reverse("otp-detail", args=(otp_devices["admin1"].pk,)))
        assert resp.status_code == 404, "Foreign user can't delete data"

        resp = clients["su"].delete(reverse("otp-detail", args=(otp_devices["admin1"].pk,)))
        assert resp.status_code == 204, "Super user can delete other user's devices"
        assert resp.cookies.get(f"otp_device_id_{users['su'].pk}") is not None, "Cookie unset"

        resp = clients["master_admin"].delete(
            reverse("otp-detail", args=(otp_devices["admin2"].pk,))
        )
        assert resp.status_code == 204, "master admin can delete other user's devices"
        assert resp.cookies.get(f"otp_device_id_{users['master_admin'].pk}") is not None, (
            "Cookie unset"
        )

        resp = clients["user1"].delete(reverse("otp-detail", args=(otp_devices["user1"].pk,)))
        assert resp.status_code == 204, "users can delete own devices devices"
        assert resp.cookies.get(f"otp_device_id_{users['user1'].pk}") is not None, "Cookie unset"

    def test_generate(self, settings, clients, users, otp_devices, mailoutbox):
        settings.OTP_ENABLED = True
        resp = clients["user1"].post(reverse("otp-generate", args=(otp_devices["user1"].pk,)))
        assert resp.status_code == 200
        request_id = resp.data["request_id"]
        otp_devices["user1"].refresh_from_db()
        token = otp_devices["user1"].token
        assert request_id in mailoutbox[0].body, "email contains request id"
        assert token in mailoutbox[0].body, "email contains token"

        resp = clients["user1"].post(reverse("otp-generate", args=(otp_devices["user1"].pk,)))
        assert resp.status_code == 200
        otp_devices["user1"].refresh_from_db()
        assert token == otp_devices["user1"].token, "token remained the same"
        assert request_id != resp.data["request_id"], "request id changed on resend"
        assert resp.data["request_id"] in mailoutbox[1].body, "email contains new request id"
        assert token in mailoutbox[1].body, "email contains the old token"

    def test_generate_email_not_verified(
        self, settings, clients, users, otp_devices, mailoutbox, disallow_eduid_login
    ):
        settings.OTP_ENABLED = True
        EmailAddress.objects.all().delete()
        resp = clients["user1"].post(reverse("otp-generate", args=(otp_devices["user1"].pk,)))
        assert resp.status_code == 400
        assert len(mailoutbox) == 0

    def test_verify(self, settings, clients, users, otp_devices):
        settings.OTP_ENABLED = True
        otp_devices["user1"].generate_token()

        resp = clients["user1"].post(
            reverse("otp-verify", args=(otp_devices["user1"].pk,)),
            {"code": otp_devices["user1"].token},
        )
        assert resp.status_code == 200
        assert resp.cookies.get(f"otp_device_id_{users['user1'].pk}") is not None, (
            "device cookie is set"
        )

    def test_verify_missing_code(self, settings, clients, users, otp_devices):
        settings.OTP_ENABLED = True
        resp = clients["user1"].post(reverse("otp-verify", args=(otp_devices["user1"].pk,)), {})
        assert resp.status_code == 400

    def test_verify_other_user(self, settings, clients, users, otp_devices):
        settings.OTP_ENABLED = True
        otp_devices["user1"].generate_token()

        resp = clients["user2"].post(
            reverse("otp-verify", args=(otp_devices["user1"].pk,)),
            {"code": otp_devices["user1"].token},
        )
        assert resp.status_code == 404
        assert resp.cookies.get(f"otp_device_id_{users['user2'].pk}") is None, (
            "device cookie is not set"
        )

    def test_verify_wrong_code(self, settings, clients, users, otp_devices):
        settings.OTP_ENABLED = True
        otp_devices["user1"].generate_token()

        resp = clients["user1"].post(
            reverse("otp-verify", args=(otp_devices["user1"].pk,)), {"code": "000000"}
        )
        assert resp.status_code == 404
        assert resp.cookies.get(f"otp_device_id_{users['user2'].pk}") is None, (
            "device cookie is not set"
        )
