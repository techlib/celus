from allauth.account.utils import send_email_confirmation, sync_user_email_addresses
from core.models import TaskProgress, User
from core.permissions import SuperuserOrAdminPermission, SuperuserPermission
from core.serializers import (
    EmailVerificationSerializer,
    TaskProgressSerializer,
    UserExtraDataSerializer,
    UserSerializer,
)
from dj_rest_auth.views import PasswordResetConfirmView
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import mail_admins
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.utils import translation
from rest_framework import mixins, status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from .signals import password_reset_signal
from .tasks import erms_sync_users_and_identities_task


class UserView(GenericAPIView):

    serializer_class = UserSerializer
    action = 'current'

    def get(self, request):
        """
        Obtains info about currently logged user
        """

        if request.user:
            request.session[translation.LANGUAGE_SESSION_KEY] = request.user.language
            return Response(UserSerializer(request.user, context={"request": request}).data)
        return HttpResponseForbidden('user is not logged in')


class SystemInfoView(GenericAPIView):

    permission_classes = [AllowAny]

    def get(self, request):
        data = {name: getattr(settings, name) for name in settings.EXPORTED_SETTINGS}
        return Response(data)


class UserLanguageView(APIView):
    def get(self, request):
        if request.user:
            return Response({'language': request.user.language})
        return HttpResponseForbidden('user is not logged in')

    def post(self, request):
        return self._set_language(request)

    def put(self, request):
        return self._set_language(request)

    def _set_language(self, request):
        if request.user:
            try:
                request.user.language = request.data.get('language')
                request.user.save()
            except ValidationError as e:
                return HttpResponseBadRequest(str(e))
            else:
                request.session[translation.LANGUAGE_SESSION_KEY] = request.user.language
                return Response({'ok': True})
        return HttpResponseForbidden('user is not logged in')


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
        return Response({'id': task.id})


class TestEmailView(APIView):

    permission_classes = [SuperuserPermission]

    def post(self, request):
        mail_admins('Email test', 'This is a test message.')
        return Response({'ok': True})


class TestErrorView(APIView):

    permission_classes = [SuperuserPermission]

    def get(self, request):
        raise Exception('test error')


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
        return HttpResponseForbidden('user is not logged in')

    def post(self, request):
        return self._set_extra_data(request)

    def put(self, request):
        return self._set_extra_data(request)

    def _set_extra_data(self, request):
        if not request.user:
            return HttpResponseForbidden('user is not logged in')

        serializer = UserExtraDataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # raises 400 exception
        # in order to distinguish between default values and the ones set by the user,
        # we use default=None in the serializer. And now we need to remove the None
        # values from the dict in order to save only the values set by the user.
        clean_data = {
            key: value for key, value in serializer.validated_data.items() if value is not None
        }
        if not clean_data:
            return Response({'error': 'no valid data supplied'}, status=status.HTTP_400_BAD_REQUEST)

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


class CeleryTaskStatusViewSet(mixins.RetrieveModelMixin, GenericViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = TaskProgressSerializer
    queryset = TaskProgress.objects.all()
    lookup_field = 'task_id'
