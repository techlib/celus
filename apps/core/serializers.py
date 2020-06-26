import typing

from datetime import datetime
from rest_framework.serializers import (
    ModelSerializer,
    SerializerMethodField,
)


from core.models import User


class UserSerializer(ModelSerializer):
    email_verification_status = SerializerMethodField()
    email_verification_sent = SerializerMethodField(required=False)

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
            'email_verification_status',
            'email_verification_sent',
        )

    def get_email_verification_status(self, obj) -> str:
        return obj.email_verification["status"]

    def get_email_verification_sent(self, obj) -> typing.Optional[datetime]:
        return obj.email_verification["email_sent"]


class UserSimpleSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ('pk', 'username', 'ext_id', 'first_name', 'last_name', 'email')
