import typing

from core.models import UL_CONS_STAFF
from core.serializers import UserSimpleSerializer
from django.db.models import Q
from organizations.models import Organization
from organizations.serializers import OrganizationSerializer
from publications.models import Platform
from publications.serializers import PlatformSerializer
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.fields import (
    BooleanField,
    CharField,
    ChoiceField,
    CurrentUserDefault,
    DateField,
    DateTimeField,
    HiddenField,
    IntegerField,
    ReadOnlyField,
    SerializerMethodField,
)
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.serializers import ModelSerializer, Serializer

from .models import (
    COUNTER_REPORTS,
    CounterReportsToCredentials,
    CounterReportType,
    SushiCredentials,
    SushiFetchAttempt,
)


class UpdateAssignedCounterReportsSerializer(Serializer):
    counter_report_id = IntegerField(min_value=1, required=True)
    credentials_id = IntegerField(min_value=1, required=True)
    last_harvestable_month = DateField(allow_null=True, required=True)


class CloneToNewerSerializer(Serializer):
    credentials_id = IntegerField(min_value=1, required=True)

    class Meta:
        fields = ("credentials_id",)


class CounterReportTypeSerializer(ModelSerializer):
    class Meta:
        model = CounterReportType
        fields = ("id", "code", "name", "counter_version")


class UnsetBrokenSerializer(Serializer):
    credentials_id = IntegerField(min_value=1, required=True)
    counter_reports = PrimaryKeyRelatedField(
        queryset=CounterReportType.objects.all(), many=True, required=False
    )

    class Meta:
        model = SushiCredentials
        fields = ("credentials_id", "counter_reports")


class CounterReportsToCredentialsSerializer(ModelSerializer):
    id = ReadOnlyField(source="counter_report_id")
    code = ReadOnlyField(source="counter_report.code")
    name = ReadOnlyField(source="counter_report.name")
    counter_version = ReadOnlyField(source="counter_report.counter_version")
    report_type = ReadOnlyField(source="counter_report.report_type_id")

    class Meta:
        model = CounterReportsToCredentials
        fields = (
            "id",
            "code",
            "name",
            "counter_version",
            "report_type",
            "broken",
            "last_harvestable_month",
            "last_harvestable_month_user_id",
            "last_harvestable_month_attempt_id",
        )


class SushiCredentialsSerializer(ModelSerializer):
    organization = OrganizationSerializer(read_only=True)
    platform = PlatformSerializer(read_only=True)
    counter_reports = PrimaryKeyRelatedField(
        queryset=CounterReportType.objects.all(), many=True, read_only=False, write_only=True
    )

    counter_reports_long = CounterReportsToCredentialsSerializer(
        many=True, source="counterreportstocredentials_set", read_only=True
    )
    organization_id = PrimaryKeyRelatedField(
        source="organization", write_only=True, queryset=Organization.objects.all()
    )
    platform_id = PrimaryKeyRelatedField(
        source="platform", write_only=True, queryset=Platform.objects.all()
    )
    locked_for_me = BooleanField(read_only=True)
    can_lock = BooleanField(read_only=True)
    submitter = HiddenField(default=CurrentUserDefault())
    locked = SerializerMethodField()
    verified = BooleanField(read_only=True)
    same_global = IntegerField(read_only=True)
    same_in_org = IntegerField(read_only=True)
    can_update = BooleanField(read_only=True)
    has_51_provider = BooleanField(read_only=True)
    forced = BooleanField(write_only=True, default=False)
    last_updated_by = UserSimpleSerializer(read_only=True)

    class Meta:
        model = SushiCredentials
        fields = (
            "pk",
            "title",
            "organization",
            "platform",
            "enabled",
            "url",
            "counter_version",
            "requestor_id",
            "customer_id",
            "http_username",
            "http_password",
            "api_key",
            "extra_params",
            "counter_reports",
            "counter_reports_long",
            "organization_id",
            "platform_id",
            "submitter",
            "locked_for_me",
            "lock_level",
            "can_lock",
            "locked",
            "outside_consortium",
            "broken",
            "verified",
            "same_global",
            "same_in_org",
            "auto_update_url",
            "forced",
            "can_update",
            "has_51_provider",
            "last_updated_by",
            "last_updated",
            "use_counter_reports_from_platform",
        )

    def get_locked(self, obj: SushiCredentials):
        return obj.lock_level >= UL_CONS_STAFF

    def alter_sushi_credentials_based_on_platform(
        self, validated_data, creds: typing.Optional[SushiCredentials] = None
    ):
        if validated_data.get("use_counter_reports_from_platform"):
            if not creds:
                # should be present in validated data
                platform: Platform = validated_data["platform"]
                counter_version = validated_data["counter_version"]
            else:
                counter_version = creds.counter_version
                platform = creds.platform

            validated_data["counter_reports"] = platform.get_counter_reports(counter_version)

    def update(self, instance: SushiCredentials, validated_data):
        # `forced` attribute is not a part of a credentails model
        # it is used to store the credentails eventhought credentials
        # with the same hash exists (otherwise 400 is triggered)
        #
        # We need to remove it here so that the credentails are updated
        # properly
        validated_data.pop("forced", None)
        # check existing credentials for this organization, platform and counter version
        if (
            SushiCredentials.objects.filter(
                organization=validated_data.get("organization") or instance.organization,
                platform=validated_data.get("platform") or instance.platform,
                counter_version=validated_data.get("counter_version") or instance.counter_version,
            )
            .exclude(pk=instance.pk)
            .exists()
        ):
            raise ValidationError(
                "Only one set of SUSHI credentials for an organization, platform and counter "
                "version is allowed."
            )
        submitter = validated_data.pop("submitter", None) or self.context["request"].user
        if not instance.can_edit(submitter):
            raise PermissionDenied("User is not allowed to edit this object - it is locked.")
        self.alter_sushi_credentials_based_on_platform(validated_data, instance)
        result: SushiCredentials = super().update(instance, validated_data)
        result.last_updated_by = submitter
        result.save()
        submitter_level = submitter.organization_relationship(result.organization_id)
        result.can_lock = submitter_level >= UL_CONS_STAFF
        result.locked_for_me = submitter_level < result.lock_level
        return result

    def create(self, validated_data):
        # `forced` attribute is not a part of a credentails model
        # it is used to store the credentails eventhought credentials
        # with the same hash exists (otherwise 400 is triggered)
        #
        # We need to remove it here so that the credentails are updated
        # properly
        validated_data.pop("forced", None)
        # check existing credentials for this organization, platform and counter version
        if SushiCredentials.objects.filter(
            organization=validated_data["organization"],
            platform=validated_data["platform"],
            counter_version=validated_data["counter_version"],
        ).exists():
            raise ValidationError(
                "Only one set of SUSHI credentials for an organization, platform and counter "
                "version is allowed."
            )
        submitter = validated_data.pop("submitter")
        self.alter_sushi_credentials_based_on_platform(validated_data)
        result = super().create(validated_data)
        result.last_updated_by = submitter
        result.save()
        submitter_level = submitter.organization_relationship(result.organization_id)
        result.can_lock = submitter_level >= UL_CONS_STAFF
        result.locked_for_me = submitter_level < result.lock_level
        return result


class SushiCredentialsNoSameGlobalSerializer(SushiCredentialsSerializer):
    same_global_allowed = False

    def _get_hash(self, validated_data, instance=None):
        instance_dict = (
            instance and {e: getattr(instance, e, None) for e in SushiCredentials.VERSION_HASH_KEYS}
        ) or {}
        return SushiCredentials.hash_version_dict(
            {
                e: validated_data.get(e, instance_dict.get(e))
                for e in SushiCredentials.VERSION_HASH_KEYS
            }
        )

    def _check_same(self, fltr, validated_data, instance=None):
        if instance:
            organization_id = (validated_data.get("organization") or instance.organization).pk
        else:
            organization_id = validated_data["organization"].pk

        if self.same_global_allowed:
            fltr = fltr & Q(organization_id=organization_id)

        same_credentials = list(
            SushiCredentials.objects.filter(fltr).values_list("organization_id", flat=True)
        )

        if same_credentials:
            if organization_id in same_credentials:
                raise ValidationError(
                    "Same credentials exists - within org", code="same-exists-within-org"
                )
            else:
                raise ValidationError(
                    "Same credentials exists - globally", code="same-exists-globally"
                )

    def create(self, validated_data):
        version_hash = self._get_hash(validated_data)

        fltr = Q(version_hash=version_hash)
        self._check_same(fltr, validated_data)

        return super().create(validated_data)

    def update(self, instance: SushiCredentials, validated_data):
        version_hash = self._get_hash(validated_data, instance)

        fltr = Q(version_hash=version_hash) & ~Q(pk=instance.pk)
        self._check_same(fltr, validated_data, instance)

        return super().update(instance, validated_data)


class SushiCredentialsNoSameInOrgSerializer(SushiCredentialsNoSameGlobalSerializer):
    same_global_allowed = True


class SushiCredentialsDataCounterReportSerializer(Serializer):
    id = IntegerField(required=True)
    code = ChoiceField(choices=[e[2] for e in COUNTER_REPORTS], required=True)
    name = CharField(allow_blank=True)
    report_type = IntegerField(required=True)


class SushiCredentialsDataReportSerializer(Serializer):
    status = ChoiceField(
        choices=("success", "no_data", "failed", "untried", "partial_data"), required=True
    )
    planned = BooleanField(required=True)
    broken = BooleanField()
    can_harvest = BooleanField()
    counter_report = SushiCredentialsDataCounterReportSerializer()


class SushiCredentialsDataSerializer(Serializer):
    year = IntegerField(required=True, max_value=3000, min_value=1970)
    for month in range(1, 13):
        locals()[f"{month:02d}"] = SushiCredentialsDataReportSerializer(many=True)


class SushiFetchAttemptSimpleSerializer(ModelSerializer):
    counter_version = IntegerField(read_only=True, source="counter_report.counter_version")

    class Meta:
        model = SushiFetchAttempt
        fields = (
            "counter_report_id",
            "counter_version",
            "credentials_id",
            "data_file",
            "file_size",
            "used_url",
            "end_date",
            "error_code",
            "import_batch",
            "pk",
            "start_date",
            "timestamp",
            "when_processed",
            "status",
            "last_updated",
        )


class SushiFetchAttemptFlatSerializer(ModelSerializer):
    class Meta:
        model = SushiFetchAttempt
        fields = (
            "counter_report",
            "credentials",
            "data_file",
            "file_size",
            "used_url",
            "end_date",
            "error_code",
            "import_batch",
            "log",
            "pk",
            "start_date",
            "timestamp",
            "when_processed",
            "partial_data",
            "status",
            "extracted_data",
            "last_updated",
        )


class SushiCleanupSerializer(Serializer):
    older_than = DateTimeField(required=False)
