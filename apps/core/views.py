from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from core.serializers import UserSerializer


class UserView(GenericAPIView):

    def get(self, request):
        if request.user:
            return Response(UserSerializer(request.user).data)
        return HttpResponseForbidden('user is not logged in')


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
                return Response({'ok': True})
        return HttpResponseForbidden('user is not logged in')


