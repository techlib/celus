from pathlib import Path

from core.models import (
    DATA_SOURCE_TYPE_ORGANIZATION,
    UL_CONS_STAFF,
    DataSource,
    SourceFileMixin,
    User,
)
from core.serializers import UserSimpleSerializer
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils.translation import gettext as _
from organizations.models import Organization
from organizations.serializers import OrganizationSerializer
from publications.logic.knowledgebase import (
    get_provider_for_counter_version,
    is_report_type_whitelisted,
)
from publications.models import Platform
from publications.serializers import (
    DataSourceSerializer,
    PlatformSerializer,
    SimplePlatformSerializer,
)
from rest_framework.exceptions import ValidationError
from rest_framework.fields import BooleanField, DateField, IntegerField, SerializerMethodField
from rest_framework.relations import StringRelatedField
from rest_framework.serializers import (
    BaseSerializer,
    CurrentUserDefault,
    HiddenField,
    ModelSerializer,
    PrimaryKeyRelatedField,
    Serializer,
)
from sushi.serializers import SushiFetchAttemptFlatSerializer

from .exceptions import MultipleReportTypes, NibblerErrors, UnsupportedReportType, WhitelistingError
from .models import (
    AccessLog,
    Dimension,
    DimensionText,
    FlexibleReport,
    FlexibleReportUserEmail,
    ImportBatch,
    InterestGroup,
    ManualDataUpload,
    MduMethod,
    Metric,
    ReportInterestMetric,
    ReportType,
    ReportTypeToDimension,
)


class OrganizationSourceExtractingMixin:
    def _get_organization_data_source(self):
        organization_id = self.context["view"].kwargs.get("organization_pk")
        if (
            self.context["request"]
            .user.accessible_organizations()
            .filter(pk=organization_id)
            .exists()
        ):
            data_source, _created = DataSource.objects.get_or_create(
                organization_id=organization_id, type=DataSource.TYPE_ORGANIZATION
            )
            return data_source
        else:
            raise ValidationError("user cannot access selected organization")


class InterestGroupSerializer(ModelSerializer):
    class Meta:
        model = InterestGroup
        fields = ("pk", "short_name", "name", "important", "position")


class MetricSerializer(ModelSerializer):
    class Meta:
        model = Metric
        fields = ("pk", "short_name", "name", "name_en", "name_cs")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get("name") == "":
            data["name"] = data.get("short_name", "")
        return data


class DimensionSerializer(OrganizationSourceExtractingMixin, ModelSerializer):
    class Meta:
        model = Dimension
        fields = ("pk", "short_name", "name", "name_cs", "name_en")
        validators = []  # this removes the implicit required validation on source

    def validate(self, attrs):
        result = super().validate(attrs)

        # extra validation for short_name in combination with source=NULL
        exclude = {"pk": attrs["pk"]} if "pk" in attrs else {}
        short_name = attrs.get("short_name")
        if Dimension.objects.exclude(**exclude).filter(short_name=short_name).exists():
            raise ValidationError(_("Dimension with this code name already exists"))

        return result


class ReportTypeSimpleSerializer(ModelSerializer):
    class Meta:
        model = ReportType
        fields = ("pk", "short_name", "name", "name_cs", "name_en", "desc")


class ReportTypeSerializer(ModelSerializer):
    controlled_metrics = PrimaryKeyRelatedField(many=True, read_only=True)
    dimensions_sorted = DimensionSerializer(many=True, read_only=True)
    public = BooleanField(default=False)
    dimensions = PrimaryKeyRelatedField(
        read_only=False, queryset=Dimension.objects.all(), many=True, write_only=True
    )
    counter_version = SerializerMethodField()
    counter_report_type_id = SerializerMethodField()
    counter_code = SerializerMethodField()
    uses_items = BooleanField(required=False)
    uses_titles = BooleanField(required=False)

    class Meta:
        model = ReportType
        fields = (
            "pk",
            "short_name",
            "name",
            "name_cs",
            "name_en",
            "desc",
            "dimensions_sorted",
            "public",
            "dimensions",
            "controlled_metrics",
            "counter_version",
            "counter_report_type_id",
            "counter_code",
            "uses_items",
            "uses_titles",
        )

    def get_counter_version(self, obj: ReportType):
        try:
            return obj.counterreporttype.counter_version
        except AttributeError:
            return None

    def get_counter_report_type_id(self, obj: ReportType):
        try:
            return obj.counterreporttype.pk
        except AttributeError:
            return None

    def get_counter_code(self, obj: ReportType):
        try:
            return obj.counterreporttype.code
        except AttributeError:
            return None

    def create(self, validated_data):
        if not validated_data["public"]:
            # this is not public, we need to get the correct source
            organization_id = self.context["view"].kwargs.get("organization_pk")
            if (
                self.context["request"]
                .user.accessible_organizations()
                .filter(pk=organization_id)
                .exists()
            ):
                data_source, _created = DataSource.objects.get_or_create(
                    organization_id=organization_id, type=DataSource.TYPE_ORGANIZATION
                )
            else:
                raise ValidationError("user cannot access selected organization")
            validated_data["source"] = data_source
        validated_data.pop("public")
        dimensions = validated_data.pop("dimensions")
        obj = super().create(validated_data)
        for i, dimension in enumerate(dimensions):
            ReportTypeToDimension.objects.update_or_create(
                report_type=obj, position=i, defaults={"dimension": dimension}
            )
        # remove any dimensions previously associated and now unwanted
        obj.reporttypetodimension_set.filter(position__gte=len(dimensions)).delete()
        # TODO: ADD TEST FOR THIS
        return obj

    def validate(self, attrs):
        result = super().validate(attrs)
        if "pk" not in attrs:
            if attrs.get("public"):
                if ReportType.objects.filter(
                    source__isnull=True, short_name=attrs.get("short_name")
                ).exists():
                    raise ValidationError(
                        _("Public report type with this code name already exists")
                    )
            else:
                organization_id = self.context["view"].kwargs.get("organization_pk")
                if ReportType.objects.filter(
                    source__organization_id=organization_id, short_name=attrs.get("short_name")
                ).exists():
                    raise ValidationError(
                        _(
                            "Report type with this code name already exists for organization "
                            '"{organization}"'
                        ).format(organization=Organization.objects.get(pk=organization_id))
                    )
        return result


class ReportInterestMetricSerializer(ModelSerializer):
    interest_group = InterestGroupSerializer(read_only=True)
    metric = MetricSerializer(read_only=True)

    class Meta:
        model = ReportInterestMetric
        fields = ("metric", "report_type", "interest_group")


class ReportTypeExtendedSerializer(ModelSerializer):
    controlled_metrics = PrimaryKeyRelatedField(many=True, read_only=True)
    dimensions_sorted = DimensionSerializer(many=True, read_only=True)
    interest_metric_set = ReportInterestMetricSerializer(
        many=True, read_only=True, source="reportinterestmetric_set"
    )
    counter_report_type = PrimaryKeyRelatedField(source="counterreporttype", read_only=True)
    source = DataSourceSerializer()

    class Meta:
        model = ReportType
        fields = (
            "pk",
            "source",
            "short_name",
            "name",
            "name_cs",
            "name_en",
            "desc",
            "dimensions_sorted",
            "interest_metric_set",
            "controlled_metrics",
            "counter_report_type",
        )


class ReportTypeInterestSerializer(ModelSerializer):
    interest_metric_set = ReportInterestMetricSerializer(
        many=True, read_only=True, source="reportinterestmetric_set"
    )

    class Meta:
        model = ReportType
        fields = (
            "pk",
            "short_name",
            "name",
            "name_cs",
            "name_en",
            "desc",
            "interest_metric_set",
            "approx_record_count",
        )


class AccessLogSerializer(BaseSerializer):
    report_type = StringRelatedField()
    organization = StringRelatedField()
    platform = StringRelatedField()
    metric = StringRelatedField()
    target = StringRelatedField()
    item = StringRelatedField()

    class Meta:
        model = AccessLog
        # fields = ('date', 'report_type', 'organization', 'platform', 'target', 'value')

    def to_representation(self, obj: AccessLog):
        data = {
            "date": obj.date.isoformat(),
            "report_type": str(obj.report_type),
            "platform": str(obj.platform),
            "organization": str(obj.organization),
            "target": str(obj.target) if obj.target else None,
            "item": str(obj.item) if obj.item else None,
            "metric": str(obj.metric),
            "value": obj.value,
        }
        data.update(getattr(obj, "mapped_dim_values_", {}))
        return data

    def get_fields(self):
        return []


class ImportBatchSerializer(ModelSerializer):
    user = UserSimpleSerializer(read_only=True)
    report_type = StringRelatedField()
    organization = StringRelatedField()
    platform = StringRelatedField()

    class Meta:
        model = ImportBatch
        fields = (
            "pk",
            "created",
            "organization",
            "platform",
            "report_type",
            "user",
            "date",
            "owner_level",
        )


class ManualDataUploadSimpleSerializer(ModelSerializer):
    class Meta:
        model = ManualDataUpload
        fields = ("pk", "data_file", "owner_level")


class ImportBatchVerboseSerializer(ModelSerializer):
    user = UserSimpleSerializer(read_only=True)
    organization = OrganizationSerializer(read_only=True)
    platform = PlatformSerializer(read_only=True)
    report_type = ReportTypeSimpleSerializer(read_only=True)
    sushifetchattempt = SushiFetchAttemptFlatSerializer(read_only=True)
    mdu = ManualDataUploadSimpleSerializer(read_only=True, many=True)

    class Meta:
        model = ImportBatch
        fields = (
            "pk",
            "created",
            "organization",
            "platform",
            "report_type",
            "user",
            "owner_level",
            "accesslog_count",
            "mdu",
            "date",
            "sushifetchattempt",
        )


class ClashingMonthsSerializer(Serializer):
    month = DateField(read_only=True)
    org_id = IntegerField(read_only=True)


class ManualDataUploadSerializer(ModelSerializer):
    user = HiddenField(default=CurrentUserDefault())
    import_batches = ImportBatchSerializer(read_only=True, many=True)
    report_type = ReportTypeExtendedSerializer(read_only=True)
    report_type_id = IntegerField(write_only=True, required=False)
    can_import = BooleanField(read_only=True)
    clashing_months = ClashingMonthsSerializer(many=True, read_only=True)

    class Meta:
        model = ManualDataUpload
        fields = (
            "pk",
            "report_type",
            "report_type_id",
            "organization",
            "platform",
            "data_file",
            "user",
            "created",
            "is_processed",
            "error",
            "error_details",
            "log",
            "import_batches",
            "preflight",
            "can_import",
            "owner_level",
            "state",
            "clashing_months",
            "method",
            "extra",
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.context["view"].action == "create":
            if attrs["method"] in [MduMethod.RAW, MduMethod.COUNTER]:
                if "report_type_id" in attrs:
                    raise ValidationError(
                        {
                            "report_type_id": "should not be present when "
                            f"`method='{attrs['method']}'`"
                        }
                    )
            else:
                if "report_type_id" not in attrs:
                    raise ValidationError({"report_type_id": "is missing"})

            platform = attrs["platform"]
            if organization := attrs.get("organization"):
                if (
                    platform.source
                    and platform.source.type == DATA_SOURCE_TYPE_ORGANIZATION
                    and platform.source.organization != organization
                ):
                    raise ValidationError(
                        {"organization": "platform is private and belongs to another organization"}
                    )
        else:
            if "report_type_id" in attrs:
                raise ValidationError(
                    {"report_type_id": "can't set report type of existing object"}
                )

        return attrs

    def _validate_whitelisting(self, mdu: ManualDataUpload):
        """
        Validate that if the detected report type requires whitelisting,
        the platform has it whitelisted in its knowledgebase.
        """
        if not mdu.report_type or not mdu.platform:
            return

        # Check if the report type has a corresponding CounterReportType that requires whitelisting
        try:
            crt = mdu.report_type.counterreporttype
            if not crt.requires_whitelisting:
                return
        except ObjectDoesNotExist:
            # No CounterReportType associated with this ReportType, no whitelisting needed
            return

        # The COUNTER report type is one that requires whitelisting
        # Check platform knowledgebase for whitelisting
        if not mdu.platform.knowledgebase:
            raise WhitelistingError(
                "Platform doesn't have knowledgebase, reports requiring whitelisting "
                "cannot be uploaded"
            )

        if not (
            kb_provider := get_provider_for_counter_version(
                mdu.platform.knowledgebase, crt.counter_version
            )
        ):
            raise WhitelistingError(
                "No provider found for counter version, reports requiring whitelisting "
                "cannot be uploaded"
            )

        if not is_report_type_whitelisted(kb_provider, crt.code):
            raise WhitelistingError(f"Report type {crt.code} is not whitelisted for platform")

    def update(self, instance: ManualDataUpload, validated_data):
        result: ManualDataUpload = super().update(instance, validated_data)
        return self._adjust_permissions(result)

    def create(self, validated_data):
        checksum, size = SourceFileMixin.checksum_fileobj(validated_data["data_file"])
        validated_data["checksum"] = checksum
        validated_data["file_size"] = size

        with transaction.atomic():
            # we put create into transaction so that when nibbler checks fails
            # nothing is created in db

            result = super().create(validated_data)
            try:
                from nibbler.logic.processing import get_errors, output_to_poops  # noqa - slow import

                # Try to parse
                nibbler_output, method = result.get_nibbler_output()

                # test whether parsing passes
                # (should raise exception when nothing is found)
                poops = output_to_poops(nibbler_output)

                # update report type in it wasn't set before
                if not result.report_type:
                    from nibbler.models import get_report_types_from_nibbler_output  # noqa - slow import

                    # update method for raw => counter transition
                    result.method = method

                    # get report type
                    report_types, rt_names = get_report_types_from_nibbler_output(poops)

                    if not rt_names:
                        # No suitable parser found
                        raise NibblerErrors(get_errors(nibbler_output))

                    if not report_types:
                        # can't resolve report type name to report type
                        # this should not happen and admin should be notified
                        # to fix the situation
                        raise UnsupportedReportType(rt_names)

                    if len({e.pk for e in report_types}) > 1:
                        # Multiple report types should not be present here
                        # that would indicate that the user uploaded e.g. xlsx file
                        # with different report type on each sheet
                        # => raise original exception
                        raise MultipleReportTypes(report_types)
                    result.extra = {p.sheet_idx: p.extras for p in poops}
                    result.report_type = report_types[0]

                    # Check whitelisting for report types that require it
                    self._validate_whitelisting(result)

                    result.save()
            except Exception:
                # remove file which won't be linked with a db model due to exception
                filepath = Path(settings.MEDIA_ROOT) / result.data_file.name
                filepath.unlink(missing_ok=True)
                raise

        return self._adjust_permissions(result)

    @classmethod
    def _adjust_permissions(cls, instance: ManualDataUpload):
        if instance.user:
            instance.owner_level = instance.user.organization_relationship(instance.organization_id)
        # we do not want to set the level too high in order for the staff to be able to edit it
        if instance.owner_level > UL_CONS_STAFF:
            instance.owner_level = UL_CONS_STAFF
        instance.save()
        return instance

    def to_representation(self, instance):
        instance.can_import = instance.can_import(self.context["request"].user)
        return super().to_representation(instance)


class ManualDataUploadVerboseSerializer(ModelSerializer):
    user = UserSimpleSerializer(read_only=True)
    platform = SimplePlatformSerializer(read_only=True)
    organization = OrganizationSerializer(read_only=True)
    report_type = ReportTypeSimpleSerializer(read_only=True)
    can_edit = BooleanField(read_only=True)

    class Meta:
        model = ManualDataUpload
        fields = (
            "pk",
            "report_type",
            "organization",
            "platform",
            "data_file",
            "user",
            "created",
            "is_processed",
            "log",
            "import_batches",
            "preflight",
            "can_edit",
            "owner_level",
            "state",
            "method",
        )


class DimensionTextSerializer(ModelSerializer):
    class Meta:
        model = DimensionText
        fields = ("pk", "text", "text_local", "text_local_en", "text_local_cs")


class FlexibleReportSerializer(ModelSerializer):
    created_by_id = PrimaryKeyRelatedField(
        queryset=User.objects.all(), write_only=True, many=False, required=False
    )
    last_updated_by_id = PrimaryKeyRelatedField(
        queryset=User.objects.all(), write_only=True, many=False, required=False
    )
    created_by = UserSimpleSerializer(read_only=True, many=False, allow_null=True)
    last_updated_by = UserSimpleSerializer(read_only=True, many=False, allow_null=True)
    mailing_count = IntegerField(read_only=True)

    class Meta:
        model = FlexibleReport
        fields = (
            "pk",
            "name",
            "description",
            "owner",
            "owner_organization",
            "last_updated",
            "last_updated_by",
            "last_updated_by_id",
            "created",
            "created_by",
            "created_by_id",
            "report_config",
            "config",
            "mailing_count",
        )

    def create(self, validated_data):
        validated_data["last_updated_by_id"] = self.context["request"].user.pk
        validated_data["created_by_id"] = self.context["request"].user.pk
        return super().create(validated_data)

    def update(self, instance: FlexibleReport, validated_data):
        validated_data["last_updated_by_id"] = self.context["request"].user.pk
        return super().update(instance, validated_data)


class PlatformInterestReportSerializer(ModelSerializer):
    interest_reports = ReportTypeInterestSerializer(many=True, read_only=True)

    class Meta:
        model = Platform
        fields = ("interest_reports", "pk", "ext_id", "short_name", "name", "provider", "url")


class FlexibleReportUserEmailNewSerializer(ModelSerializer):
    last_sent = DateField(read_only=True)

    class Meta:
        model = FlexibleReportUserEmail
        fields = (
            "pk",
            "flexible_report",
            "user",
            "frequency",
            "fiscal_period",
            "number_of_periods",
            "last_sent",
        )


class FlexibleReportUserEmailSerializer(ModelSerializer):
    user = UserSimpleSerializer(read_only=True)
    last_updated_by = UserSimpleSerializer(read_only=True)

    class Meta:
        model = FlexibleReportUserEmail
        fields = (
            "pk",
            "flexible_report",
            "user",
            "frequency",
            "fiscal_period",
            "number_of_periods",
            "last_sent",
            "next_send",
            "last_updated_by",
            "last_updated",
        )

    def create(self, validated_data):
        validated_data["last_updated_by_id"] = self.context["request"].user.pk
        return super().create(validated_data)

    def update(self, instance: FlexibleReportUserEmail, validated_data):
        validated_data["last_updated_by_id"] = self.context["request"].user.pk
        return super().update(instance, validated_data)


class FlexibleReportUserEmailCreateSerializer(FlexibleReportUserEmailSerializer):
    user = PrimaryKeyRelatedField(queryset=User.objects.all(), required=True)

    def validate(self, attrs):
        fr: FlexibleReport = attrs.get(
            "flexible_report", self.instance.flexible_report if self.instance else None
        )
        if fr and fr.report_config.get("trend_mode"):
            if attrs["number_of_periods"] % 2 != 0:
                raise ValidationError("Number of periods cannot be odd if trend mode is active")
        return attrs
