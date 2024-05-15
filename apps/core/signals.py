from allauth.account.models import EmailAddress
from allauth.account.signals import user_signed_up
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import Signal, receiver
from django_otp.plugins.otp_email.models import EmailDevice

from core.models import User

from .tasks import async_mail_customer_care_admins

password_reset_signal = Signal()


@receiver(user_signed_up)
def mail_about_user_signing_up(request, user, **kwargs):
    async_mail_customer_care_admins.delay(
        f"New account created - {user.username}",
        f"""\
New user account was created.

Username: {user.username}
Email: {user.email}""",
    )


@receiver(password_reset_signal)
def verify_user_email(request, user, **kwargs):
    """
    After successful password reset, we take the users default email as verified.
    Also, if the appropriate `EmailAddress` instance does not exist, we create it.
    """
    if user.email and not user.email_verified:
        email_obj, created = EmailAddress.objects.get_or_create(
            user=user, email=user.email, defaults={"verified": True}
        )
        if not created:
            email_obj.verified = True
            email_obj.save()


@receiver(post_save, sender=User)
def email_device_should_exist_when_user_is_saved(sender, instance, created, **kwargs):
    """
    After user is created or updated we make sure that appropriate EmailDevice exists
    """
    if settings.OTP_ENABLED and settings.OTP_CREATE_EMAIL_DEVICES:
        EmailDevice.objects.get_or_create(
            user=instance, name="default", defaults={"confirmed": True, "email": None}
        )
