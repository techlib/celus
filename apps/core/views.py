from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.utils import translation
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import SuperuserOrAdminPermission
from core.serializers import UserSerializer

from .tasks import erms_sync_users_and_identities_task


class UserView(GenericAPIView):

    def get(self, request):
        if request.user:
            translation.activate(request.user.language)
            request.session[translation.LANGUAGE_SESSION_KEY] = request.user.language
            return Response(UserSerializer(request.user).data)
        return HttpResponseForbidden('user is not logged in')


class SystemInfoView(GenericAPIView):

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
                translation.activate(request.user.language)
                request.session[translation.LANGUAGE_SESSION_KEY] = request.user.language
                return Response({'ok': True})
        return HttpResponseForbidden('user is not logged in')


class StartERMSSyncUsersAndIdentitiesTask(APIView):

    permission_classes = [SuperuserOrAdminPermission]

    def post(self, request):
        task = erms_sync_users_and_identities_task.delay()
        return Response({
            'id': task.id,
        })
