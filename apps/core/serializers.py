from rest_framework.serializers import ModelSerializer, Serializer

from core.models import User


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = (
            'pk',
            'username',
            'ext_id',
            'first_name',
            'last_name',
            'email',
            'language',
            'is_from_master_organization',
            'is_superuser',
        )


class UserSimpleSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ('pk', 'username', 'ext_id', 'first_name', 'last_name', 'email')
