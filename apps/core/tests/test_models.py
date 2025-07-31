import pytest
from allauth.account.models import EmailAddress
from django_otp.plugins.otp_email.models import EmailDevice

from core.models import User
from test_scenarios.basic import *  # noqa


@pytest.mark.django_db
def test_accessible_platforms(basic1):  # noqa
    # master admin/user can access all platforms
    assert list(basic1["users"]["master_admin"].accessible_platforms()) == sorted(
        basic1["platforms"].values(), key=lambda x: x.name
    )
    assert list(basic1["users"]["master_user"].accessible_platforms()) == sorted(
        basic1["platforms"].values(), key=lambda x: x.name
    )

    assert list(basic1["users"]["admin1"].accessible_platforms()) == [
        basic1["platforms"]["brain"],  # API source => public
        basic1["platforms"]["branch"],  # suborganization of root
        basic1["platforms"]["empty"],  # no source => public
        basic1["platforms"]["master"],  # API source => public
        basic1["platforms"]["root"],  # admin of root
        basic1["platforms"]["shared"],  # no source => public
    ]

    assert list(basic1["users"]["admin2"].accessible_platforms()) == [
        basic1["platforms"]["brain"],  # API source => public
        basic1["platforms"]["empty"],  # no source => public
        basic1["platforms"]["master"],  # API source => public
        basic1["platforms"]["shared"],  # no source => public
        basic1["platforms"]["standalone"],  # admin of standalone
    ]

    assert list(basic1["users"]["user1"].accessible_platforms()) == [
        basic1["platforms"]["brain"],  # API source => public
        basic1["platforms"]["branch"],  # member of branch organization
        basic1["platforms"]["empty"],  # no source => public
        basic1["platforms"]["master"],  # API source => public
        basic1["platforms"]["shared"],  # no source => public
    ]

    assert list(basic1["users"]["user2"].accessible_platforms()) == [
        basic1["platforms"]["brain"],  # API source => public
        basic1["platforms"]["empty"],  # no source => public
        basic1["platforms"]["master"],  # API source => public
        basic1["platforms"]["shared"],  # no source => public
        basic1["platforms"]["standalone"],  # member of standalone organization
    ]

    # test with organization defined
    assert list(
        basic1["users"]["user2"].accessible_platforms(basic1["organizations"]["standalone"])
    ) == [
        basic1["platforms"]["brain"],  # API source => public
        basic1["platforms"]["empty"],  # no source => public
        basic1["platforms"]["master"],  # API source => public
        basic1["platforms"]["shared"],  # no source => public
        basic1["platforms"]["standalone"],  # member of standalone organization
    ]

    assert list(basic1["users"]["user2"].accessible_platforms(basic1["organizations"]["root"])) == [
        basic1["platforms"]["brain"],  # API source => public
        basic1["platforms"]["empty"],  # no source => public
        basic1["platforms"]["master"],  # API source => public
        basic1["platforms"]["shared"],  # no source => public
    ]

    assert list(
        basic1["users"]["admin1"].accessible_platforms(basic1["organizations"]["root"])
    ) == [
        basic1["platforms"]["brain"],  # API source => public
        basic1["platforms"]["empty"],  # no source => public
        basic1["platforms"]["master"],  # API source => public
        basic1["platforms"]["root"],  # admin of root
        basic1["platforms"]["shared"],  # no source => public
    ]

    assert list(
        basic1["users"]["admin1"].accessible_platforms(basic1["organizations"]["branch"])
    ) == [
        basic1["platforms"]["brain"],  # API source => public
        basic1["platforms"]["branch"],  # suborganization of root
        basic1["platforms"]["empty"],  # no source => public
        basic1["platforms"]["master"],  # API source => public
        basic1["platforms"]["shared"],  # no source => public
    ]


@pytest.mark.django_db
class TestUserModel:
    @pytest.mark.parametrize(
        ["allow_eduid_login", "verified", "user_email_verified"],
        [[True, True, True], [True, False, True], [False, True, True], [False, False, False]],
    )
    def test_email_verification_case_mismatch(
        self, settings, allow_eduid_login, verified, user_email_verified
    ):
        """
        Test that email is considered verified even if the case is changed
        """
        settings.ALLOW_EDUID_LOGIN = allow_eduid_login
        user = User.objects.create(username="foo", email="foo@bar.baz")
        EmailAddress.objects.create(user=user, email=user.email, verified=verified)
        assert user.email_verified == user_email_verified
        # now change the case of the email in one place
        user.email = user.email.capitalize()
        user.save()
        # .email_verified is a cached property, we need new User instance
        user = User.objects.get(pk=user.pk)
        assert user.email_verified == user_email_verified, (
            "the email should be verified even if case does not match"
        )

    @pytest.mark.parametrize(["otp_enabled", "created"], [[True, True], [False, False]])
    def test_email_device_created_on_signal(self, settings, otp_enabled, created):
        settings.OTP_ENABLED = otp_enabled
        settings.OTP_CREATE_EMAIL_DEVICES = True
        assert EmailDevice.objects.count() == 0
        User.objects.create(username="foo", email="foo@bar.baz")
        if created:
            assert EmailDevice.objects.count() == 1
        else:
            assert EmailDevice.objects.count() == 0
