import typing
from datetime import datetime

from allauth.account.forms import default_token_generator
from allauth.account.utils import url_str_to_user_pk as uid_decoder
from django.conf import settings
from django.utils.encoding import force_str
from django_otp import DEVICE_ID_SESSION_KEY, devices_for_user, user_has_device
from django_otp.plugins.otp_email.models import EmailDevice
from organizations.models import Organization, UserOrganization
from organizations.serializers import OrganizationShortSerializer
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import (
    BooleanField,
    CharField,
    ChoiceField,
    DateTimeField,
    IntegerField,
    ModelSerializer,
    PrimaryKeyRelatedField,
    Serializer,
    SerializerMethodField,
)
from sesame.utils import get_token

from core.models import TaskProgress, User


class EmailVerificationSerializer(Serializer):
    status = ChoiceField(User.EMAIL_VERIFICATION_STATUSES, read_only=True)
    email_sent = DateTimeField(read_only=True, default=None)


class EmailDeviceSerializer(ModelSerializer):
    class Meta:
        fields = ("pk", "email", "name", "confirmed")
        model = EmailDevice

    def validate(self, attrs):
        result = super().validate(attrs)
        user = self.context["request"].user
        if not user.email_verified:
            raise ValidationError({"user": "user's email is not verified"})
        return result

    def create(self, validated_data):
        device = EmailDevice.objects.create(
            user=self.context["request"].user,
            name=validated_data["name"],
            confirmed=True,
            email=None,
        )
        return device


class UserSerializer(ModelSerializer):
    otp_required = SerializerMethodField()
    email_verification_status = SerializerMethodField()
    email_verification_sent = SerializerMethodField(required=False)
    sesame_token = SerializerMethodField()
    impersonator = PrimaryKeyRelatedField(read_only=True, required=False)

    class Meta:
        model = User
        fields = (
            "pk",
            "username",
            "ext_id",
            "first_name",
            "last_name",
            "email",
            "language",
            "is_user_of_master_organization",
            "is_admin_of_master_organization",
            "is_superuser",
            "is_staff",
            "otp_required",
            "email_verification_status",
            "email_verification_sent",
            "extra_data",
            "impersonator",
            "sesame_token",
        )

    def get_email_verification_status(self, obj: User) -> str:
        return obj.email_verification["status"]

    def get_email_verification_sent(self, obj: User) -> typing.Optional[datetime]:
        return obj.email_verification["email_sent"]

    def get_otp_required(self, obj: User) -> typing.Optional[typing.List[dict]]:
        if not settings.OTP_ENABLED or obj.skip_2fa:
            # OTP disabled
            return None

        if request := self.context.get("request"):
            # User needs to have device activated
            if user_has_device(request.real_user):
                # Test whether device matches
                device_id = request.session.get(DEVICE_ID_SESSION_KEY)
                user_devices = devices_for_user(request.real_user)
                # Only emails are currently supported
                user_devices = [e for e in user_devices if isinstance(e, EmailDevice)]
                if device_id in [e.persistent_id for e in user_devices]:
                    return None  # 2FA is activated

                res = []
                for device in user_devices:
                    serializer = EmailDeviceSerializer(device)
                    data = serializer.data
                    # EmailDevice allows you to override email
                    # when override is not used fill in User.email here
                    data["email"] = data.get("email") or request.real_user.email
                    res.append(data)

                return res

        # No need for 2FA
        return None

    def to_representation(self, instance: User):
        if impersonator_user := self.context["request"].impersonator:
            instance.impersonator = impersonator_user.pk
        else:
            instance.impersonator = None
        return super().to_representation(instance)

    def get_sesame_token(self, instance: User) -> str:
        if self.get_otp_required(instance):
            # 2FA is required, so we don't want to return the token
            # otherwise it would create a side channel for bypassing 2FA
            return ""
        return get_token(instance)


class UserSimpleSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ("pk", "username", "ext_id", "first_name", "last_name", "email")


class UserExtraDataSerializer(Serializer):
    basic_tour_finished = BooleanField(required=False, allow_null=True, default=None)
    last_dismissed_release = CharField(required=False, allow_null=True, default=None, max_length=20)
    last_seen_release = CharField(required=False, allow_null=True, default=None, max_length=20)
    fiscal_year_start_month = IntegerField(
        required=False,
        allow_null=True,
        default=None,
        min_value=0,
        max_value=11,
        help_text="Month using javascript notation - 0-11, where 0 is January, 1 is February, etc.",
    )


class TaskProgressSerializer(ModelSerializer):
    class Meta:
        model = TaskProgress
        fields = (
            "task_id",
            "status",
            "task_name",
            "worker",
            "date_created",
            "date_done",
            "progress_total",
            "progress_current",
        )


class UserOrganizationSerializer(ModelSerializer):
    organization = OrganizationShortSerializer(read_only=True)

    class Meta:
        model = UserOrganization
        fields = ("organization", "is_admin")


class AccessibleUsersSerializer(ModelSerializer):
    organizations = UserOrganizationSerializer(
        source="userorganization_set", many=True, read_only=True
    )

    is_admin = BooleanField(write_only=True, required=False)  # neccessary for post
    organization = PrimaryKeyRelatedField(
        write_only=True, queryset=Organization.objects.all(), required=False
    )  # neccessary for post

    class Meta:
        model = User
        fields = (
            "pk",
            "first_name",
            "last_name",
            "username",
            "email",
            "is_superuser",
            "organizations",
            "is_admin",
            "organization",
            "is_admin_of_master_organization",
        )

    def create(self, validated_data):
        admin_rights = validated_data.pop("is_admin")
        organization = validated_data.pop("organization")

        user = User.objects.create(**validated_data)
        UserOrganization.objects.create(user=user, organization=organization, is_admin=admin_rights)
        return user

    def update(self, instance, validated_data):
        instance.email = validated_data.get("email", instance.email)
        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.username = validated_data.get("username", instance.username)
        instance.save()

        if "organization" in validated_data:
            admin_rights = validated_data.pop("is_admin")
            organization = validated_data.pop("organization")
            UserOrganization.objects.update_or_create(
                user=instance, organization=organization, defaults={"is_admin": admin_rights}
            )

        return instance


class EduIdIdentityConfirmSerializer(serializers.Serializer):
    """
    Serializer for validation of an invitation/reset token
    """

    uid = serializers.CharField()
    token = serializers.CharField()
    user = None

    def validate(self, attrs):
        # Decode the uidb64 (allauth use base36) to uid to get User object
        try:
            uid = force_str(uid_decoder(attrs["uid"]))
            self.user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise ValidationError({"uid": ["Invalid value"]}) from None

        if not default_token_generator.check_token(self.user, attrs["token"]):
            raise ValidationError({"token": ["Invalid value"]})

        return attrs
