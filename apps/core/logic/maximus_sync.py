import logging
from typing import Optional

from django.conf import settings
from logs.models import FlexibleReport, OrganizationPlatform
from organizations.models import Organization, UserOrganization
from publications.models import Platform
from rest_framework import serializers
from sushi.models import CounterReportsToCredentials, SushiCredentials

from ..models import User

logger = logging.getLogger(__name__)


class CelusUserSerializer(serializers.ModelSerializer):
    ext_id = serializers.IntegerField(source="id")
    skip_2fa = serializers.SerializerMethodField()

    def get_skip_2fa(self, obj: User) -> Optional[bool]:
        if not settings.OTP_ENABLED:
            return None
        return obj.skip_2fa

    class Meta:
        model = User
        fields = (
            "ext_id",
            "username",
            "first_name",
            "last_name",
            "email",
            "date_joined",
            "last_login",
            "is_active",
            "skip_2fa",
        )


class CelusOrganizationSerializer(serializers.ModelSerializer):
    ext_id = serializers.IntegerField(source="id")
    master_organization = serializers.ReadOnlyField(source="is_master_organization")

    class Meta:
        model = Organization
        fields = ("ext_id", "name", "short_name", "raw_data_import_enabled", "master_organization")


class CelusUserOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserOrganization
        fields = ("user", "organization", "is_admin")


class CelusOrganizationPlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationPlatform
        fields = ("organization", "platform")


class CallableRelatedField(serializers.SlugRelatedField):
    def to_representation(self, obj):
        return getattr(obj, self.slug_field)()


class CelusPlatformSerializer(serializers.ModelSerializer):
    # platform already has a ext_id field and in new version of DRF overshadowing it here
    # does not work. For this reason, we use pk instead and remap it later in `get_platforms`
    source = serializers.StringRelatedField()
    source_type = CallableRelatedField(
        read_only=True, slug_field="get_type_display", source="source"
    )

    class Meta:
        model = Platform
        fields = ("pk", "short_name", "name", "source", "source_type", "counter_registry_id")


class CounterReportsToCredentialsSerializer(serializers.ModelSerializer):
    counter_report_type = serializers.SlugRelatedField(
        slug_field="code", read_only=True, source="counter_report"
    )

    class Meta:
        model = CounterReportsToCredentials
        fields = ("counter_report_type", "broken")


class SushiCredentialsSerializer(serializers.ModelSerializer):
    ext_id = serializers.IntegerField(source="id")
    counter_reports = CounterReportsToCredentialsSerializer(
        many=True, source="counterreportstocredentials_set"
    )
    verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = SushiCredentials
        fields = (
            "ext_id",
            "organization",
            "platform",
            "url",
            "counter_version",
            "requestor_id",
            "customer_id",
            "http_username",
            "http_password",
            "api_key",
            "extra_params",
            "enabled",
            "counter_reports",
            "outside_consortium",
            "lock_level",
            "broken",
            "verified",
        )


class FlexibleReportSerializer(serializers.ModelSerializer):
    ext_id = serializers.IntegerField(source="id")

    class Meta:
        model = FlexibleReport
        fields = (
            "ext_id",
            "name",
            "created",
            "last_updated",
            "owner",
            "owner_organization",
            "report_config",
        )


def get_organizations():
    return CelusOrganizationSerializer(Organization.objects.all(), many=True).data


def get_users():
    return CelusUserSerializer(User.objects.all(), many=True).data


def get_users_organizations():
    return CelusUserOrganizationSerializer(UserOrganization.objects.all(), many=True).data


def get_organizations_platforms():
    return CelusOrganizationPlatformSerializer(OrganizationPlatform.objects.all(), many=True).data


def get_platforms():
    data = CelusPlatformSerializer(
        Platform.objects.all().select_related("source", "source__organization"), many=True
    ).data
    for p in data:
        p["ext_id"] = p.pop("pk")
    return data


def get_sushi_credentials():
    return SushiCredentialsSerializer(
        SushiCredentials.objects.all()
        .prefetch_related("counterreportstocredentials_set__counter_report")
        .annotate_verified(),
        many=True,
    ).data


def get_flexible_reports():
    return FlexibleReportSerializer(FlexibleReport.objects.all(), many=True).data


def sync():
    if not settings.MAXIMUS_URL or not settings.MAXIMUS_TOKEN:
        logger.warning("MAXIMUS_URL/MAXIMUS_TOKEN not set - not syncing")
        return

    import requests  # noqa - slow import

    c = requests.session()
    c.headers["Authorization"] = "Api-Key " + settings.MAXIMUS_TOKEN
    d = {
        "/organizations/": get_organizations,
        "/users/": get_users,
        "/users-organizations/": get_users_organizations,
        "/platforms/": get_platforms,
        "/organizations-platforms/": get_organizations_platforms,
        "/sushi-credentials/": get_sushi_credentials,
        "/flexible-reports/": get_flexible_reports,
    }
    for k, v in d.items():
        payload = v()
        resp = c.post(settings.MAXIMUS_URL + k, json=payload)
        if resp.status_code >= 400:
            from core.tasks import async_mail_admins

            async_mail_admins(
                f"Failed to sync {k} to Maximus",
                f"Failed to sync {k} to Maximus: {resp.status_code}\n\nError:\n{resp.text}\n\n"
                f"Payload:\n{payload}",
            )
