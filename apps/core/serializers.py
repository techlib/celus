import typing
from datetime import datetime

from django_celery_results.models import TaskResult
from rest_framework.serializers import (
    BooleanField,
    ChoiceField,
    DateTimeField,
    IntegerField,
    ModelSerializer,
    PrimaryKeyRelatedField,
    Serializer,
    SerializerMethodField,
    CharField,
)

from core.models import TaskProgress, User


class EmailVerificationSerializer(Serializer):
    status = ChoiceField(User.EMAIL_VERIFICATION_STATUSES, read_only=True)
    email_sent = DateTimeField(read_only=True, default=None)


class UserSerializer(ModelSerializer):
    email_verification_status = SerializerMethodField()
    email_verification_sent = SerializerMethodField(required=False)
    impersonator = PrimaryKeyRelatedField(read_only=True, required=False)

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
            'is_user_of_master_organization',
            'is_admin_of_master_organization',
            'is_superuser',
            'is_staff',
            'email_verification_status',
            'email_verification_sent',
            'extra_data',
            'impersonator',
        )

    def get_email_verification_status(self, obj) -> str:
        return obj.email_verification["status"]

    def get_email_verification_sent(self, obj) -> typing.Optional[datetime]:
        return obj.email_verification["email_sent"]

    def to_representation(self, instance):
        if impersonator_user := self.context["request"].impersonator:
            instance.impersonator = impersonator_user.pk
        else:
            instance.impersonator = None
        return super().to_representation(instance)


class UserSimpleSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ('pk', 'username', 'ext_id', 'first_name', 'last_name', 'email')


class UserExtraDataSerializer(Serializer):
    basic_tour_finished = BooleanField(required=False, allow_null=True, default=None)
    last_dismissed_release = CharField(required=False, allow_null=True, default=None)
    last_seen_release = CharField(required=False, allow_null=True, default=None)


class TaskProgressSerializer(ModelSerializer):
    class Meta:
        model = TaskProgress
        fields = (
            'task_id',
            'status',
            'task_name',
            'worker',
            'date_created',
            'date_done',
            'progress_total',
            'progress_current',
        )
