import base64
import codecs
import logging
import platform
import secrets
from contextlib import redirect_stderr, redirect_stdout
from datetime import timedelta
from io import StringIO

import prometheus_client
from allauth.account.adapter import get_adapter
from decouple import RepositoryEnv
from dj_rest_auth.registration.views import VerifyEmailView
from dj_rest_auth.views import PasswordResetConfirmView
from django.conf import settings
from django.contrib.auth.admin import sensitive_post_parameters_m
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import mail_admins
from django.core.management import call_command
from django.db import IntegrityError
from django.db.models import Prefetch
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.utils.timezone import now
from django.views import View
from django_otp import DEVICE_ID_SESSION_KEY, match_token
from django_otp.plugins.otp_email.models import EmailDevice, GenerateNotAllowed
from organizations.models import UserOrganization
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ViewSet

from config.permissions import IsAuthenticatedWithOptional2FA
from core.account import sync_user_email_addresses
from core.logic.email import mail_otp_token
from core.models import UL_ORG_ADMIN, Identity, TaskProgress, User
from core.permissions import OwnerPermission, SuperuserOrAdminPermission, SuperuserPermission
from core.serializers import (
    AccessibleUsersSerializer,
    EduIdIdentityConfirmSerializer,
    EmailDeviceSerializer,
    EmailVerificationSerializer,
    TaskProgressSerializer,
    UserExtraDataSerializer,
    UserSerializer,
)

from .apps import version_to_int
from .logic.management_commands import CommandManager
from .logic.type_conversion import to_bool
from .prometheus import (
    CACHE_STORED_GAUAGES,
    cache_based_metrics,
    celus_os_info,
    celus_python_info,
    celus_registry,
    celus_sentry_release,
    celus_version_num,
)
from .signals import password_reset_signal
from .tasks import erms_sync_users_and_identities_task

logger = logging.getLogger(__name__)


class UserView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserSerializer
    action = "current"

    def get(self, request):
        """
        Obtains info about currently logged user
        """
        if request.user:
            return Response(UserSerializer(request.user, context={"request": request}).data)
        return HttpResponseForbidden("user is not logged in")

    def get_queryset(self):
        return super().get_queryset().annotate_can_impersonate()


class UserExistsView(GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if check := request.GET.get("hmac"):
            if User.objects.raw(
                "SELECT * FROM core_user WHERE encode(hmac(lower(trim(email)), %s, %s), 'hex') = "
                "%s LIMIT 1",
                [settings.OCTOPUS_HMAC_KEY, settings.OCTOPUS_HMAC_ALGO, check],
            ):
                return Response({"exists": True})
        return Response({"exists": False})


class SystemInfoView(GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        data = {name: getattr(settings, name) for name in settings.EXPORTED_SETTINGS}
        return Response(data)


class UserLanguageView(APIView):
    def get(self, request):
        if request.user:
            return Response({"language": request.user.language})
        return HttpResponseForbidden("user is not logged in")

    def post(self, request):
        return self._set_language(request)

    def put(self, request):
        return self._set_language(request)

    def _set_language(self, request):
        if request.user:
            try:
                request.user.language = request.data.get("language")
                request.user.save()
            except ValidationError as e:
                return HttpResponseBadRequest(str(e))
            else:
                return Response({"ok": True})
        return HttpResponseForbidden("user is not logged in")


class UserVerifyEmailView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = EmailVerificationSerializer

    def post(self, request):
        user: User = request.user
        email_address = sync_user_email_addresses(user)

        # Don't send email if already verified
        if not user.email_verified:
            email_address.send_confirmation(request, signup=False)

        del user.email_verification  # reload cached property
        return Response(self.serializer_class(user.email_verification).data)


class StartERMSSyncUsersAndIdentitiesTask(APIView):
    permission_classes = [SuperuserOrAdminPermission]

    def post(self, request):
        task = erms_sync_users_and_identities_task.delay()
        return Response({"id": task.id})


class TestEmailView(APIView):
    permission_classes = [SuperuserPermission]

    def post(self, request):
        mail_admins("Email test", "This is a test message.")
        return Response({"ok": True})


class TestErrorView(APIView):
    permission_classes = [SuperuserPermission]

    def get(self, request):
        raise Exception("test error")


class UserExtraDataView(APIView):
    """
    Allows storage of extra data into the user.extra_data field.
    It uses a predefined dictionary of keys and value types, so that it protects against attacks
    where users would store huge arbitrary values in the database.
    We enforce this on the API level and not on the model level, because we want the freedom
    to store anything inside our code - the protection is applied just to the public API
    """

    def get(self, request):
        if request.user:
            return Response(request.user.extra_data)
        return HttpResponseForbidden("user is not logged in")

    def post(self, request):
        return self._set_extra_data(request)

    def put(self, request):
        return self._set_extra_data(request)

    def _set_extra_data(self, request):
        if not request.user:
            return HttpResponseForbidden("user is not logged in")

        serializer = UserExtraDataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # raises 400 exception
        # in order to distinguish between default values and the ones set by the user,
        # we use default=None in the serializer. And now we need to remove the None
        # values from the dict in order to save only the values set by the user.
        clean_data = {
            key: value for key, value in serializer.validated_data.items() if value is not None
        }
        if not clean_data:
            return Response({"error": "no valid data supplied"}, status=status.HTTP_400_BAD_REQUEST)

        request.user.extra_data.update(clean_data)
        request.user.save()
        return Response(request.user.extra_data)


class UserPasswordResetView(PasswordResetConfirmView):
    """
    We have to extend the rest-auth `PasswordResetConfirmView` in order to emit a signal
    on successful reset
    """

    def post(self, request, *args, **kwargs):
        """
        We extend the parent implementation in order to insert a signal. Unfortunatelly we have
        to duplicate part of the parent code, but it is probably better than replacing it
        completely
        """
        # serialization is done in parent method as well, but we do it once more to get to the
        # user instance which we need for the signal
        # also, we need to do the serialization before we call super().post, because once
        # it is fully processed, the token will no longer be valid and validation will fail
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid()  # populates serializer.user
        response = super().post(request, *args, **kwargs)
        password_reset_signal.send(self.__class__, request=request, user=serializer.user)
        return response


class VerifyEmailAndOtpView(VerifyEmailView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._object = None

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200 and settings.OTP_ENABLED:
            obj = self.get_object()  # this is EmailConfirmation for the current email address
            user = obj.email_address.user
            device, _created = EmailDevice.objects.get_or_create(
                user=user, name="default", defaults={"confirmed": True, "email": None}
            )
            device.confirmed = True
            device.save()
            OtpDeviceView._set_cookie(response, user, device)
        return response

    def get_object(self):
        # cache call to get_object because it would be invalidated by the first call
        # inside super().post
        if self._object is None:
            self._object = super().get_object()
        return self._object


class CeleryTaskStatusViewSet(mixins.RetrieveModelMixin, GenericViewSet):
    permission_classes = (IsAuthenticatedWithOptional2FA,)
    serializer_class = TaskProgressSerializer
    queryset = TaskProgress.objects.all()
    lookup_field = "task_id"


class ManagementCommandViewSet(ViewSet):
    permission_classes = (IsAuthenticatedWithOptional2FA, SuperuserPermission)
    lookup_field = "name"

    def list(self, request):
        out = []
        cm = CommandManager()
        for ci in cm.commands:
            args = [ci.serialize_arg(arg) for arg in ci.args]
            out.append(
                {"name": ci.name, "help": ci.instance.help, "uses_doit": ci.uses_doit, "args": args}
            )
        return Response(out)

    @action(detail=True, methods=["post"])
    def run(self, request, name=None):
        """
        This is where one command is executed. The command name is passed in the `name` field
        and the arguments are passed in the `args` field as a dictionary.
        """
        cm = CommandManager()
        if not (ci := cm.get_command_by_name(name)):
            return Response({"error": "command not found"}, status=status.HTTP_404_NOT_FOUND)

        args = []
        options = {}
        # unfortunately it is not possible to pass all the args as options (kwargs) to
        # `call_command` - we need to split them into args and options to be given separately
        for arg in ci.args:
            if arg.dest in request.data:
                value = request.data[arg.dest]
                typ = ci.arg_type_str(arg)
                if typ == "bool":
                    value = to_bool(value)
                elif typ == "int":
                    value = int(value)
                elif typ == "file":
                    # value is a file-like object in binary mode
                    # we need to convert it to a text stream if the argument expects it
                    if arg.type._encoding:
                        value = codecs.getreader(arg.type._encoding)(value)

                if arg.required:
                    args.append(value)
                else:
                    options[arg.dest] = value
        if ci.uses_doit:
            options["doit"] = to_bool(request.data.get("doit", False))

        # capture the output of the command
        out = StringIO()
        err = StringIO()
        log = StringIO()
        root_logger = logging.getLogger()
        formatter = logging.Formatter("%(levelname)s:: %(message)s")
        handler = logging.StreamHandler(log)
        handler.setLevel(logging.INFO)  # do not let DEBUG messages through
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

        exception = None
        try:
            with redirect_stdout(out), redirect_stderr(err):
                # redirect_stdout and redirect_stderr seem to do the same job as passing
                # stdout and stderr to call_command, but they would also call print()
                # which is what we want because we cannot ensure all the commands use
                # .stdout and .stderr
                # On the other hand, redirect_stdout and redirect_stderr do not work
                # with call_command when the instance was created outside the context
                # so using both together ensures that the output is captured in all cases
                call_command(ci.instance, *args, stdout=out, stderr=err, **options)
        except Exception as e:
            exception = str(e)
        finally:
            root_logger.removeHandler(handler)
        return Response(
            {
                "stdout": out.getvalue(),
                "stderr": err.getvalue(),
                "exception": exception,
                "log": log.getvalue(),
            }
        )


class AccessibleUsersViewSet(ModelViewSet):
    serializer_class = AccessibleUsersSerializer

    def get_queryset(self):
        current_user = self.request.user
        queryset = current_user.accessible_users().prefetch_related(
            "userorganization_set__organization",
            Prefetch(
                "userorganization_set",
                queryset=UserOrganization.objects.select_related("organization"),
                to_attr="userorganization_set_prefetched",
            ),
        )
        return queryset

    def check_user_permissions(self, request, org_pk):
        user_role = request.user.organization_relationship(org_id=org_pk)
        if settings.ALLOW_ORG_ADMINS_TO_MANAGE_USERS:  # Organization admins can manage users
            if user_role < UL_ORG_ADMIN:
                raise PermissionDenied(
                    "You are not allowed to manage users as you are not an admin of this "
                    "organization."
                )
        # Only consortial admins + superusers can manage users
        elif not (request.user.is_admin_of_master_organization or request.user.is_superuser):
            raise PermissionDenied(
                "You are not allowed to manage users as you are not a consortial admin."
            )

    @action(detail=True, methods=["post"], url_path="delete-org-relation")
    def delete_relation(self, request, pk):
        org_pk = request.data.get("organization")

        self.check_user_permissions(request, org_pk)

        if int(pk) == int(request.user.pk):  # pk is the same as request user pk
            return Response(
                {"detail": "You cannot delete your own account."}, status=status.HTTP_403_FORBIDDEN
            )

        else:
            user_org_instance = UserOrganization.objects.get(user=pk, organization=org_pk)
            unlinked_user = user_org_instance.user
            if (
                not unlinked_user.userorganization_set.exclude(pk=user_org_instance.pk).exists()
                and not unlinked_user.is_superuser
            ):
                # delete users whithout organization (excluding superusers)
                unlinked_user.delete()
                return Response({"detail": "User was deleted."}, status=status.HTTP_200_OK)
            else:
                user_org_instance.delete()
                return Response(
                    {"detail": "User has been removed from the organization."},
                    status=status.HTTP_200_OK,
                )

    def create(self, request, *args, **kwargs):
        org_pk = request.data.get("organization")
        # check whether the request.user is allowed to add to this org
        self.check_user_permissions(request, org_pk)
        try:
            return super().create(request)
        except IntegrityError as e:
            # the unique email problem should be covered by the serializer, but just in case
            # we catch the exception here (a race condition could happen, for example)
            if "unique-user-email" in str(e):
                return Response(
                    {"email": ["User with this email already exists"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DifferentUserInviteView(APIView):
    permission_classes = (IsAuthenticatedWithOptional2FA,)
    serializer_class = EmailVerificationSerializer

    def post(self, request):
        user = User.objects.get(pk=request.data.get("pk"))
        adapter = get_adapter()
        adapter.send_invitation_email(request, user)
        return Response(self.serializer_class(user.email_verification).data)


class DifferentUserVerifyEmailView(APIView):
    permission_classes = (IsAuthenticatedWithOptional2FA,)
    serializer_class = EmailVerificationSerializer

    def post(self, request):
        user = User.objects.get(pk=request.data.get("pk"))
        email_address = sync_user_email_addresses(user)

        # Don't send email if already verified
        if not user.email_verified:
            email_address.send_confirmation(request, signup=False)
            verification_status = "verification email sent"
        else:
            verification_status = "already verified"

        del user.email_verification  # reload cached property

        response_data = {
            "verification_status": verification_status,
            "email_verification_data": self.serializer_class(user.email_verification).data,
        }

        return Response(response_data)


class OtpDeviceView(
    mixins.ListModelMixin, mixins.DestroyModelMixin, mixins.CreateModelMixin, GenericViewSet
):
    permission_classes = [SuperuserOrAdminPermission | OwnerPermission]
    serializer_class = EmailDeviceSerializer

    @staticmethod
    def _set_cookie(response, user, device):
        max_age = timedelta(days=settings.OTP_VERIFICATION_VALIDITY)

        response.set_signed_cookie(
            f"{DEVICE_ID_SESSION_KEY}_{user.pk}",
            device.persistent_id,
            max_age=max_age,
            httponly=True,  # don't let js access this cookie
        )

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)

        # set cookie right away so that user is not forced
        # to login and logout when OTP login is switched on (toggle button is pressed)
        if response.status_code == status.HTTP_201_CREATED:
            device = EmailDevice.objects.filter(user=self.request.user).order_by("id").last()
            OtpDeviceView._set_cookie(response, request.user, device)

        return response

    def destroy(self, request, *args, **kwargs):
        response = super().destroy(request, *args, **kwargs)
        # Unset cookie so it doesn't mess up future 2FA
        if response.status_code == status.HTTP_204_NO_CONTENT:
            response.delete_cookie(f"{DEVICE_ID_SESSION_KEY}_{request.user.pk}")
        return response

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.is_admin_of_master_organization:
            return EmailDevice.objects.all()
        else:
            return EmailDevice.objects.filter(user=user)

    def random(self) -> str:
        return base64.b64encode(secrets.token_bytes(20)).decode()[:10]

    @action(detail=True, methods=["post"])
    def generate(self, request, pk):
        device = self.get_object()
        generate_allowed, data_dict = device.generate_is_allowed()

        if not request.user.email_verified:
            # can't sent token using unverified email
            return Response(
                {"error": "user's email is not verified"}, status=status.HTTP_400_BAD_REQUEST
            )

        if generate_allowed:
            # generate new token
            device.cooldown_set(commit=False)
            device.generate_token(valid_secs=settings.OTP_EMAIL_TOKEN_VALIDITY, commit=True)

        elif not data_dict or data_dict["reason"] != GenerateNotAllowed.COOLDOWN_DURATION_PENDING:
            # Currently can't generate token
            return Response(
                {"error": "can't generate token for this device"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request_id = self.random()
        mail_otp_token(
            device.email or self.request.user.email,
            request_id,
            device.token,
            self.request.user.language,
        )
        return Response({"request_id": request_id})

    @action(detail=True, methods=["post"])
    def verify(self, request, pk):
        # read code / token
        token = request.data.get("code")
        if not token:
            return Response({"code": "missing field"}, status=status.HTTP_400_BAD_REQUEST)

        if device := match_token(request.user, token):
            # no need to set anything special to request
            # after setting this cookie otp_required will be set to null
            response = Response()
            OtpDeviceView._set_cookie(response, request.user, device)

            return response

        # couldn't find token
        return Response({"token": "token not valid"}, status=status.HTTP_404_NOT_FOUND)


class PrometheusMetricsView(View):
    @classmethod
    def get_os_info(cls):
        try:
            return platform.freedesktop_os_release()
        except AttributeError:
            return RepositoryEnv("/etc/os-release").data

    def get(self, request):
        # update the cache-based metrics (those are not updated automatically, but rather a celery
        # task is getting the data and pushing it to the cache, from where we get it)
        for name, params in CACHE_STORED_GAUAGES.items():
            dims = params.get("dims", [])
            value = cache.get(name, {} if dims else 0)
            if dims:
                for labels, val in value.items():
                    cache_based_metrics[name].labels(*labels).set(val)
            else:
                cache_based_metrics[name].set(value)

        celus_version_num.set(version_to_int(settings.CELUS_VERSION))
        celus_sentry_release.labels(hash=settings.SENTRY_RELEASE).set(1.0)
        os_info = self.get_os_info()
        celus_os_info.labels(
            name=os_info.get("NAME", "unknown"),
            version=os_info.get("VERSION", "unknown"),
            version_id=os_info.get("VERSION_ID", "unknown"),
            version_codename=os_info.get("VERSION_CODENAME", "unknown"),
            pretty_name=os_info.get("PRETTY_NAME", "unknown"),
        ).set(1.0)
        major, minor, micro = platform.python_version_tuple()
        celus_python_info.labels(
            version=platform.python_version(), major=str(major), minor=str(minor), micro=str(micro)
        ).set(1.0)

        metrics_page = prometheus_client.generate_latest(celus_registry)
        return HttpResponse(metrics_page, content_type=prometheus_client.CONTENT_TYPE_LATEST)


class EduIdIdentityConfirmView(GenericAPIView):
    """
    Used to connect the identity obtained from the eduID service with the user in the system.
    Uses a system similar to the password reset/invitation confirmation view.
    """

    serializer_class = EduIdIdentityConfirmSerializer
    permission_classes = (AllowAny,)

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if identity_value := request.META.get(settings.EDUID_IDENTITY_HEADER):
            identity_obj, created = Identity.objects.get_or_create(
                identity=identity_value, defaults={"user": serializer.user}
            )
            if not created and identity_obj.user != serializer.user:
                logger.warning(
                    "Identity %s reassigned from %s to user %s",
                    identity_value,
                    identity_obj.user,
                    serializer.user,
                )
                identity_obj.user = serializer.user
                identity_obj.save()
            # force update of the last_login field to invalidate the verification token
            serializer.user.last_login = now()
            serializer.user.save()
            return Response(
                {"detail": f"Identity '{identity_value}' assigned to user '{serializer.user}'."}
            )
        else:
            return Response(
                {"detail": "No identity header found."}, status=status.HTTP_400_BAD_REQUEST
            )
