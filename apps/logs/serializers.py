from pathlib import Path

from core.models import UL_CONS_STAFF, DataSource, SourceFileMixin
from core.serializers import UserSimpleSerializer
from django.conf import settings
from django.db import transaction
from django.utils.translation import gettext as _
from nibbler.logic.processing import get_errors, output_to_poops
from nibbler.models import get_report_types_from_nibbler_output
from organizations.models import Organization
from organizations.serializers import OrganizationSerializer
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
    ListField,
    ModelSerializer,
    PrimaryKeyRelatedField,
)
from sushi.serializers import SushiFetchAttemptFlatSerializer

from .exceptions import MultipleReportType, NibblerErrors
from .models import (
    AccessLog,
    Dimension,
    DimensionText,
    FlexibleReport,
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
        organization_id = self.context['view'].kwargs.get('organization_pk')
        if (
            self.context['request']
            .user.accessible_organizations()
            .filter(pk=organization_id)
            .exists()
        ):
            data_source, _created = DataSource.objects.get_or_create(
                organization_id=organization_id, type=DataSource.TYPE_ORGANIZATION
            )
            return data_source
        else:
            raise ValidationError('user cannot access selected organization')


class InterestGroupSerializer(ModelSerializer):
    class Meta:
        model = InterestGroup
        fields = ('pk', 'short_name', 'name', 'important', 'position')


class MetricSerializer(ModelSerializer):
    class Meta:
        model = Metric
        fields = ('pk', 'short_name', 'name', 'name_en', 'name_cs')


class DimensionSerializer(OrganizationSourceExtractingMixin, ModelSerializer):
    class Meta:
        model = Dimension
        fields = ('pk', 'short_name', 'name', 'name_cs', 'name_en')
        validators = []  # this removes the implicit required validation on source

    def validate(self, attrs):
        result = super().validate(attrs)

        # extra validation for short_name in combination with source=NULL
        exclude = {'pk': attrs['pk']} if 'pk' in attrs else {}
        short_name = attrs.get('short_name')
        if Dimension.objects.exclude(**exclude).filter(short_name=short_name).exists():
            raise ValidationError(_('Dimension with this code name already exists'))

        return result


class ReportTypeSimpleSerializer(ModelSerializer):
    class Meta:
        model = ReportType
        fields = ('pk', 'short_name', 'name', 'name_cs', 'name_en', 'desc')


class ReportTypeSerializer(ModelSerializer):

    controlled_metrics = PrimaryKeyRelatedField(many=True, read_only=True)
    dimensions_sorted = DimensionSerializer(many=True, read_only=True)
    public = BooleanField(default=False)
    dimensions = PrimaryKeyRelatedField(
        read_only=False, queryset=Dimension.objects.all(), many=True, write_only=True
    )
    counter_version = SerializerMethodField()
    counter_report_type_id = SerializerMethodField()

    class Meta:
        model = ReportType
        fields = (
            'pk',
            'short_name',
            'name',
            'name_cs',
            'name_en',
            'desc',
            'dimensions_sorted',
            'public',
            'dimensions',
            'controlled_metrics',
            'counter_version',
            'counter_report_type_id',
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

    def create(self, validated_data):
        if not validated_data['public']:
            # this is not public, we need to get the correct source
            organization_id = self.context['view'].kwargs.get('organization_pk')
            if (
                self.context['request']
                .user.accessible_organizations()
                .filter(pk=organization_id)
                .exists()
            ):
                data_source, _created = DataSource.objects.get_or_create(
                    organization_id=organization_id, type=DataSource.TYPE_ORGANIZATION
                )
            else:
                raise ValidationError('user cannot access selected organization')
            validated_data['source'] = data_source
        validated_data.pop('public')
        dimensions = validated_data.pop('dimensions')
        obj = super().create(validated_data)
        for i, dimension in enumerate(dimensions):
            ReportTypeToDimension.objects.update_or_create(
                report_type=obj, position=i, defaults={'dimension': dimension}
            )
        # remove any dimensions previously associated and now unwanted
        obj.reporttypetodimension_set.filter(position__gte=len(dimensions)).delete()
        # TODO: ADD TEST FOR THIS
        return obj

    def validate(self, attrs):
        result = super().validate(attrs)
        if 'pk' not in attrs:
            if attrs.get('public'):
                if ReportType.objects.filter(
                    source__isnull=True, short_name=attrs.get('short_name')
                ).exists():
                    raise ValidationError(
                        _('Public report type with this code name already exists')
                    )
            else:
                organization_id = self.context['view'].kwargs.get('organization_pk')
                if ReportType.objects.filter(
                    source__organization_id=organization_id, short_name=attrs.get('short_name')
                ).exists():
                    raise ValidationError(
                        _(
                            'Report type with this code name already exists for organization '
                            '"{organization}"'
                        ).format(organization=Organization.objects.get(pk=organization_id))
                    )
        return result


class ReportInterestMetricSerializer(ModelSerializer):

    interest_group = InterestGroupSerializer(read_only=True)
    metric = MetricSerializer(read_only=True)
    target_metric = MetricSerializer(read_only=True)

    class Meta:
        model = ReportInterestMetric
        fields = ('metric', 'report_type', 'target_metric', 'interest_group')


class ReportTypeExtendedSerializer(ModelSerializer):

    controlled_metrics = PrimaryKeyRelatedField(many=True, read_only=True)
    dimensions_sorted = DimensionSerializer(many=True, read_only=True)
    interest_metric_set = ReportInterestMetricSerializer(
        many=True, read_only=True, source='reportinterestmetric_set'
    )
    counter_report_type = PrimaryKeyRelatedField(source='counterreporttype', read_only=True)
    source = DataSourceSerializer()

    class Meta:
        model = ReportType
        fields = (
            'pk',
            'source',
            'short_name',
            'name',
            'name_cs',
            'name_en',
            'desc',
            'dimensions_sorted',
            'interest_metric_set',
            'controlled_metrics',
            'counter_report_type',
        )


class ReportTypeInterestSerializer(ModelSerializer):

    interest_metric_set = ReportInterestMetricSerializer(
        many=True, read_only=True, source='reportinterestmetric_set'
    )
    # used_by_platforms is added as an annotation in one case where it is important
    # it is a number of platforms that use this report type to define interest
    used_by_platforms = IntegerField(read_only=True, default=0)

    class Meta:
        model = ReportType
        fields = (
            'pk',
            'short_name',
            'name',
            'name_cs',
            'name_en',
            'desc',
            'interest_metric_set',
            'approx_record_count',
            'used_by_platforms',
        )


class AccessLogSerializer(BaseSerializer):

    report_type = StringRelatedField()
    organization = StringRelatedField()
    platform = StringRelatedField()
    metric = StringRelatedField()
    target = StringRelatedField()

    class Meta:
        model = AccessLog
        # fields = ('date', 'report_type', 'organization', 'platform', 'target', 'value')

    def to_representation(self, obj: AccessLog):
        data = {
            'date': obj.date.isoformat(),
            'report_type': str(obj.report_type),
            'platform': str(obj.platform),
            'organization': str(obj.organization),
            'target': str(obj.target) if obj.target else None,
            'metric': str(obj.metric),
            'value': obj.value,
        }
        data.update(getattr(obj, 'mapped_dim_values_', {}))
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
            'pk',
            'created',
            'organization',
            'platform',
            'report_type',
            'user',
            'date',
            'owner_level',
        )


class ManualDataUploadSimpleSerializer(ModelSerializer):
    class Meta:
        model = ManualDataUpload
        fields = ('pk', 'data_file', 'owner_level')


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
            'pk',
            'created',
            'organization',
            'platform',
            'report_type',
            'user',
            'owner_level',
            'accesslog_count',
            'mdu',
            'date',
            'sushifetchattempt',
        )


class ManualDataUploadSerializer(ModelSerializer):

    user = HiddenField(default=CurrentUserDefault())
    import_batches = ImportBatchSerializer(read_only=True, many=True)
    report_type = ReportTypeExtendedSerializer(read_only=True)
    report_type_id = IntegerField(write_only=True, required=False)
    can_edit = BooleanField(read_only=True)
    can_import = BooleanField(read_only=True)
    clashing_months = ListField(child=DateField(), read_only=True)

    class Meta:
        model = ManualDataUpload
        fields = (
            'pk',
            'report_type',
            'report_type_id',
            'organization',
            'platform',
            'data_file',
            'user',
            'created',
            'is_processed',
            'error',
            'error_details',
            'log',
            'import_batches',
            'preflight',
            'can_edit',
            'can_import',
            'owner_level',
            'state',
            'clashing_months',
            'method',
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.context['view'].action == "create":
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
        else:
            if "report_type_id" in attrs:
                raise ValidationError(
                    {"report_type_id": "can't set report type of existing object"}
                )

        return attrs

    def update(self, instance: ManualDataUpload, validated_data):
        result = super().update(instance, validated_data)  # type: Annotation
        return self._adjust_permissions(result)

    def create(self, validated_data):
        checksum, size = SourceFileMixin.checksum_fileobj(validated_data['data_file'])
        validated_data['checksum'] = checksum
        validated_data['file_size'] = size

        with transaction.atomic():
            # we put create into transaction so that when nibbler checks fails
            # nothing is created in db

            result = super().create(validated_data)
            try:
                if ManualDataUpload.using_nibbler_cls(validated_data["method"]):
                    # Try to parse
                    nibbler_output, method = result.get_nibbler_output()

                    # test whether parsing passes
                    # (should raise exception when nothing is found)
                    poops = output_to_poops(nibbler_output)

                    # update report type in it wasn't set before
                    if not result.report_type:

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
                            raise RuntimeError(f"Can't resolve {rt_names} to ReportType")

                        if len({e.pk for e in report_types}) > 1:
                            # Multiple report types should not be present here
                            # that would indicate that the user uploaded e.g. xlsx file
                            # with different report type on each sheet
                            # => raise original exception
                            raise MultipleReportType(
                                f"Multiple ReportTypes found in the data: {rt_names}"
                            )
                        result.report_type = report_types[0]
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
            'pk',
            'report_type',
            'organization',
            'platform',
            'data_file',
            'user',
            'created',
            'is_processed',
            'log',
            'import_batches',
            'preflight',
            'can_edit',
            'owner_level',
            'state',
            'method',
        )


class DimensionTextSerializer(ModelSerializer):
    class Meta:
        model = DimensionText
        fields = ('pk', 'text', 'text_local', 'text_local_en', 'text_local_cs')


class FlexibleReportSerializer(ModelSerializer):

    last_updated_by = HiddenField(default=CurrentUserDefault())

    class Meta:
        model = FlexibleReport
        fields = (
            'pk',
            'name',
            'owner',
            'owner_organization',
            'last_updated',
            'last_updated_by',
            'created',
            'report_config',
            'config',
        )


class PlatformInterestReportSerializer(ModelSerializer):
    interest_reports = ReportTypeInterestSerializer(many=True, read_only=True)

    class Meta:
        model = Platform
        fields = ('interest_reports', 'pk', 'ext_id', 'short_name', 'name', 'provider', 'url')
