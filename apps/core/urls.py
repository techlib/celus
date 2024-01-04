from django.conf import settings
from django.urls import path
from rest_framework.routers import DefaultRouter, SimpleRouter

from . import views

router = DefaultRouter()
router.register(r"task-status", views.CeleryTaskStatusViewSet, basename="task-status")


router.register(
    r"management/command", views.ManagementCommandViewSet, basename="management-command"
)

if settings.ALLOW_USER_MANAGEMENT:
    router.register(r"user-management", views.AccessibleUsersViewSet, basename="user-management")


urlpatterns = [
    path("user/", views.UserView.as_view(), name="user_api_view"),
    path("user/language", views.UserLanguageView.as_view(), name="user_lang_api_view"),
    path(
        "user/verify-email", views.UserVerifyEmailView.as_view(), name="user_api_verify_email_view"
    ),
    path(
        "user/verify-email-code",
        views.VerifyEmailAndOtpView.as_view(),
        name="user_verify_email_code",
    ),
    path("user/extra-data", views.UserExtraDataView.as_view(), name="user_extra_data_view"),
    path("user/password-reset", views.UserPasswordResetView.as_view(), name="user_password_reset"),
    path("user/exists", views.UserExistsView.as_view(), name="user_exists_api_view"),
    path("info/", views.SystemInfoView.as_view(), name="system_info_api_view"),
    path(
        "run-task/erms-sync-users-and-identities",
        views.StartERMSSyncUsersAndIdentitiesTask.as_view(),
    ),
    path("test-email/", views.TestEmailView.as_view(), name="test_email_api_view"),
    path("test-error/", views.TestErrorView.as_view(), name="test_error_api_view"),
    path(
        "send-verification-email/",
        views.DifferentUserVerifyEmailView.as_view(),
        name="send_verification_email",
    ),
    path(
        "send-invitation-email/",
        views.DifferentUserInviteView.as_view(),
        name="send_invitation_email",
    ),
] + router.urls


if settings.OTP_ENABLED:
    otp_router = SimpleRouter()
    otp_router.register("otp", views.OtpDeviceView, basename="otp")
    urlpatterns += otp_router.urls
