from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError
from rest_framework.fields import IntegerField, DateField, BooleanField
from rest_framework.relations import StringRelatedField, PrimaryKeyRelatedField
from rest_framework.serializers import (
    ModelSerializer,
    BaseSerializer,
    HiddenField,
    CurrentUserDefault,
)

from core.models import DataSource, UL_CONS_STAFF
from core.serializers import UserSerializer, UserSimpleSerializer
from organizations.models import Organization
from organizations.serializers import OrganizationSerializer
from publications.serializers import (
    PlatformSerializer,
    DataSourceSerializer,
    SimplePlatformSerializer,
)
from sushi.serializers import SushiFetchAttemptFlatSerializer
from .models import (
    Metric,
    Dimension,
    ReportType,
    ManualDataUpload,
    InterestGroup,
    AccessLog,
    ImportBatch,
    ReportTypeToDimension,
    ReportInterestMetric,
    DimensionText,
    FlexibleReport,
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

    public = BooleanField(default=False)

    class Meta:
        model = Dimension
        fields = ('pk', 'short_name', 'name', 'name_cs', 'name_en', 'type', 'source', 'public')
        validators = []  # this removes the implicit required validation on source

    def validate(self, attrs):
        result = super().validate(attrs)
        # extra validation for short_name in combination with source=NULL
        exclude = {'pk': attrs['pk']} if 'pk' in attrs else {}
        short_name = attrs.get('short_name')
        if attrs.get('public'):
            if (
                Dimension.objects.exclude(**exclude)
                .filter(source__isnull=True, short_name=short_name)
                .exists()
            ):
                raise ValidationError(_('Public dimension with this code name already exists'))
        else:
            source = self._get_organization_data_source()
            if (
                Dimension.objects.exclude(**exclude)
                .filter(source=source, short_name=short_name)
                .exists()
            ):
                raise ValidationError(_('Dimension with this code name already exists'))
        return result

    def create(self, validated_data):
        # we need to make sure source is properly assigned for non-public dimensions
        if not validated_data.get('source') and not validated_data['public']:
            validated_data['source'] = self._get_organization_data_source()
        validated_data.pop('public')
        return super().create(validated_data)


class ReportTypeSimpleSerializer(ModelSerializer):
    class Meta:
        model = ReportType
        fields = ('pk', 'short_name', 'name', 'name_cs', 'name_en', 'desc')


class ReportTypeSerializer(ModelSerializer):

    dimensions_sorted = DimensionSerializer(many=True, read_only=True)
    log_count = IntegerField(read_only=True)
    newest_log = DateField(read_only=True)
    oldest_log = DateField(read_only=True)
    public = BooleanField(default=False)
    dimensions = PrimaryKeyRelatedField(
        read_only=False, queryset=Dimension.objects.all(), many=True, write_only=True
    )

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
            'log_count',
            'newest_log',
            'oldest_log',
            'public',
            'dimensions',
        )

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

    dimensions_sorted = DimensionSerializer(many=True, read_only=True)
    used_metrics = MetricSerializer(many=True, read_only=True)
    interest_metric_set = ReportInterestMetricSerializer(
        many=True, read_only=True, source='reportinterestmetric_set'
    )
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
            'used_metrics',
            'interest_metric_set',
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
            'target': str(obj.target),
            'metric': str(obj.metric),
            'value': obj.value,
        }
        data.update(getattr(obj, 'mapped_dim_values_', {}))
        return data

    def get_fields(self):
        return []


class ImportBatchSerializer(ModelSerializer):

    user = UserSerializer(read_only=True)
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
            'owner_level',
        )


class ManualDataUploadSimpleSerializer(ModelSerializer):
    class Meta:
        model = ManualDataUpload
        fields = (
            'pk',
            'data_file',
            'owner_level',
        )


class ImportBatchVerboseSerializer(ModelSerializer):

    user = UserSerializer(read_only=True)
    organization = OrganizationSerializer(read_only=True)
    platform = PlatformSerializer(read_only=True)
    report_type = ReportTypeSerializer(read_only=True)
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
            'extra',
            'can_edit',
            'owner_level',
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        return attrs

    def update(self, instance: ManualDataUpload, validated_data):
        result = super().update(instance, validated_data)  # type: Annotation
        return self._adjust_permissions(result)

    def create(self, validated_data):
        result = super().create(validated_data)
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
            'extra',
            'can_edit',
            'owner_level',
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
