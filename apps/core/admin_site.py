from django.conf import settings
from django.contrib import admin
from django_otp import user_has_device


class CelusAdminSite(admin.AdminSite):
    def has_permission(self, request):
        # Check for OTP in admin only when otp is enabled
        # and debug is turned off
        if (
            settings.OTP_ENABLED
            and not settings.DEBUG
            and user_has_device(request.user)
            and not request.real_user.is_verified()
            and not request.real_user.skip_2fa
        ):
            return False

        return super().has_permission(request)
