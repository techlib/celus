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
        f'{settings.EMAIL_SUBJECT_PREFIX}{subject}', message, settings.SERVER_EMAIL, addresses
    )
