from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from core.serializers import UserSerializer


class UserView(GenericAPIView):

    def get(self, request):
        if request.user:
            return Response(UserSerializer(request.user).data)
