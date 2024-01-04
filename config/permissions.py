from datetime import datetime, timedelta

from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from django_otp import user_has_device
from rest_framework.permissions import IsAuthenticated


class IsAuthenticatedWithOptional2FA(IsAuthenticated):
    """
    Check whether user is authenticated and optionally checks for 2FA
    """

    # Timeout which is used to limit sending of huge number of emails
    # when user doesn't have valid OTP device.
    # (in seconds)
    ADMIN_NOTIFICATION_EMAIL_TIMEOUT = 60 * 60 * 24

    def has_permission(self, request, view):
        from django.conf import settings

        res = super().has_permission(request, view)
        if res and settings.OTP_ENABLED:
            has_device = user_has_device(request.user)
            if not has_device:
                # User without a device have be allowed to login, but
                # a notification will be sent
                value = cache.get(f"otp_missing_device_{request.real_user.pk}")
                if not value or datetime.fromisoformat(value) < timezone.now():
                    # make sure that emails are not sent too often
                    from core.tasks import async_mail_admins

                    path = reverse("admin:otp_email_emaildevice_changelist")
                    url = request.build_absolute_uri(path)
                    async_mail_admins.delay(
                        f"User {request.real_user} doesn't have valid otp device",
                        f"This can be fixed in {url}",
                    )
                    cache.set(
                        f"otp_missing_device_{request.real_user.pk}",
                        (
                            timezone.now()
                            + timedelta(seconds=self.ADMIN_NOTIFICATION_EMAIL_TIMEOUT)
                        ).isoformat(),
                        timeout=self.ADMIN_NOTIFICATION_EMAIL_TIMEOUT,
                    )

            elif has_device and hasattr(request.real_user, "is_verified"):
                # Impersonate is used -> is_verified is set only for real user
                return request.real_user.is_verified()

        return res
