from rest_framework.serializers import ModelSerializer

from core.models import User


class UserSerializer(ModelSerializer):

    class Meta:
        model = User
        fields = ('pk', 'username', 'ext_id', 'first_name', 'last_name', 'email')
