import typing
from datetime import datetime

from organizations.models import Organization, UserOrganization
from organizations.serializers import OrganizationShortSerializer
from rest_framework.serializers import (
    BooleanField,
    CharField,
    ChoiceField,
    DateTimeField,
    ModelSerializer,
    PrimaryKeyRelatedField,
    Serializer,
    SerializerMethodField,
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


class UserOrganizationSerializer(ModelSerializer):
    organization = OrganizationShortSerializer(read_only=True)

    class Meta:
        model = UserOrganization
        fields = ('organization', 'is_admin')


class AccessibleUsersSerializer(ModelSerializer):
    organizations = UserOrganizationSerializer(
        source='userorganization_set', many=True, read_only=True
    )

    is_admin = BooleanField(write_only=True, required=False)  # neccessary for post
    organization = PrimaryKeyRelatedField(
        write_only=True, queryset=Organization.objects.all(), required=False
    )  # neccessary for post

    class Meta:
        model = User
        fields = (
            'pk',
            'first_name',
            'last_name',
            'username',
            'email',
            'is_superuser',
            'organizations',
            'is_admin',
            'organization',
            'is_admin_of_master_organization',
        )

    def create(self, validated_data):
        admin_rights = validated_data.pop('is_admin')
        organization = validated_data.pop('organization')

        user = User.objects.create(**validated_data)
        UserOrganization.objects.create(user=user, organization=organization, is_admin=admin_rights)
        return user

    def update(self, instance, validated_data):
        instance.email = validated_data.get('email', instance.email)
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.username = validated_data.get('username', instance.username)
        instance.save()

        if 'organization' in validated_data:
            admin_rights = validated_data.pop('is_admin')
            organization = validated_data.pop('organization')
            UserOrganization.objects.update_or_create(
                user=instance, organization=organization, defaults={'is_admin': admin_rights}
            )

        return instance
