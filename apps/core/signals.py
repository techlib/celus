from allauth.account.signals import user_signed_up
from django.dispatch import receiver

from .tasks import async_mail_admins


@receiver(user_signed_up)
def mail_about_user_signing_up(request, user, **kwargs):
    async_mail_admins.delay(
        "New account created",
        "New user account was created.\n\nUsername: {0.username}\nEmail: {0.email}".format(user),
    )
