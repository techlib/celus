from django.conf import settings
from django.core.mail import send_mail


def mail_customer_care_admins(subject, message):
    """Send a message to the customer care admins - inspired by django `mail_admins`."""
    if not settings.CUSTOMER_CARE_ADMINS:
        return
    # CUSTOMER_CARE_ADMINS is a list of 2-tuples (name, email) - this is enforced in the
    # `check_customer_care_admins` check in apps/core/apps.py
    addresses = [a[1] for a in settings.CUSTOMER_CARE_ADMINS]
    send_mail(
        f"{settings.EMAIL_SUBJECT_PREFIX}{subject}", message, settings.SERVER_EMAIL, addresses
    )


def mail_otp_token(email, request_id, token, language: str = "en"):
    if language == "cs":
        subject = "Celus - Dvoufázová autentizace"
        msg = f"""\
Zde je kód pro přihlášení k Vašemu účtu v Celusu (požadavek {request_id}):

    {token}

Tento email byl odeslán, protože byl proveden pokus o příhlášení k vašemu účtu v Celusu, \
který je spárovaný s Vaší emailovou adresou. Pokud se nesnažíte do svého účtu přihlásit, \
změňte si neprodleně Vaše heslo v Celusu.
"""

    else:
        subject = "Celus - Two phase authentication"
        msg = f"""\
Here is the access code for your recent login into Celus (request {request_id}):

    {token}

This email was sent because of a recent login attempt into your Celus account which included your
 correct email and password. If you are not trying to log in into your Celus account,
 you should change your Celus password immediately.
"""
    send_mail(subject, msg, settings.SERVER_EMAIL, [email])
