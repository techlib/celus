import base64
import codecs
import logging
import secrets
from contextlib import redirect_stderr, redirect_stdout
from datetime import timedelta
from io import StringIO

from allauth.account.adapter import get_adapter
from allauth.account.utils import send_email_confirmation, sync_user_email_addresses
from dj_rest_auth.registration.views import VerifyEmailView
from dj_rest_auth.views import PasswordResetConfirmView
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import mail_admins
from django.core.management import call_command
from django.db.models import Prefetch
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django_otp import DEVICE_ID_SESSION_KEY, match_token
from django_otp.plugins.otp_email.models import EmailDevice, GenerateNotAllowed
from organizations.models import UserOrganization
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ViewSet

from config.permissions import IsAuthenticatedWithOptional2FA
from core.logic.email import mail_otp_token
from core.models import TaskProgress, User
from core.permissions import OwnerPermission, SuperuserOrAdminPermission, SuperuserPermission
from core.serializers import (
    AccessibleUsersSerializer,
    EmailDeviceSerializer,
    EmailVerificationSerializer,
    TaskProgressSerializer,
    UserExtraDataSerializer,
    UserSerializer,
)

from .logic.management_commands import CommandManager
from .logic.type_conversion import to_bool
from .signals import password_reset_signal
from .tasks import erms_sync_users_and_identities_task


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
        sync_user_email_addresses(user)

        # Don't send email if already verified
        if not user.email_verified:
            send_email_confirmation(request, user, signup=False)

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

    @action(detail=True, methods=["post"], url_path="delete-org-relation")
    def delete_relation(self, request, pk):
        org_pk = request.data.get("organization")

        if request.user.organization_relationship(org_id=request.data.get("organization")) < 300:
            return Response(
                {"detail": "You are not admin of this organization."},
                status=status.HTTP_403_FORBIDDEN,
            )

        elif int(pk) == int(request.user.pk):  # pk is the same as request user pk
            return Response(
                {"detail": "You cannot delete your own account."}, status=status.HTTP_403_FORBIDDEN
            )

        else:
            user_org_instance = UserOrganization.objects.get(user=pk, organization=org_pk)
            user_org_instance.delete()
            return Response(
                {"detail": "User has been removed from the organization."},
                status=status.HTTP_200_OK,
            )

    def create(self, request):
        # check whether the request.user is allowed to add to this org
        if request.user.organization_relationship(org_id=request.data.get("organization")) < 300:
            return Response(
                {"detail": "You are not admin of this organization."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return super().create(request)


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
        sync_user_email_addresses(user)

        # Don't send email if already verified
        if not user.email_verified:
            send_email_confirmation(request, user, signup=False)
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
