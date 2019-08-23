from django.utils.translation import gettext as _

from rest_framework.exceptions import NotAuthenticated, ValidationError
from rest_framework.fields import CharField, IntegerField, DateField, BooleanField
from rest_framework.relations import StringRelatedField
from rest_framework.serializers import ModelSerializer, BaseSerializer, HiddenField, \
    CurrentUserDefault

from core.models import DataSource
from core.serializers import UserSerializer
from logs.models import AccessLog, ImportBatch
from organizations.models import Organization
from organizations.serializers import OrganizationSerializer
from publications.serializers import PlatformSerializer
from .models import Metric, Dimension, ReportType, ManualDataUpload


class MetricSerializer(ModelSerializer):

    class Meta:
        model = Metric
        fields = ('pk', 'short_name', 'name')


class DimensionSerializer(ModelSerializer):

    # type = CharField(source='get_type_display')

    class Meta:
        model = Dimension
        fields = ('pk', 'short_name', 'name', 'name_cs', 'name_en', 'type')


class ReportTypeSerializer(ModelSerializer):

    dimensions_sorted = DimensionSerializer(many=True, read_only=True)
    log_count = IntegerField(read_only=True)
    newest_log = DateField(read_only=True)
    oldest_log = DateField(read_only=True)
    interest_groups = BooleanField(read_only=True)
    public = BooleanField()

    class Meta:
        model = ReportType
        fields = ('pk', 'short_name', 'name', 'name_cs', 'name_en', 'desc', 'dimensions_sorted',
                  'log_count', 'newest_log', 'oldest_log', 'public', 'interest_groups')

    def create(self, validated_data):
        if not validated_data['public']:
            # this is not public, we need to get the correct source
            organization_id = self.context['view'].kwargs.get('organization_pk')
            if self.context['request'].user.accessible_organizations().filter(pk=organization_id).exists():
                data_source, _crated = DataSource.objects.get_or_create(
                    organization_id=organization_id, type=DataSource.TYPE_ORGANIZATION)
            else:
                raise ValidationError('user cannot access selected organization')
            validated_data['source'] = data_source
        validated_data.pop('public')
        return super().create(validated_data)

    def validate(self, attrs):
        result = super().validate(attrs)
        if 'pk' not in attrs:
            if attrs.get('public'):
                if ReportType.objects.filter(source__isnull=True,
                                             short_name=attrs.get('short_name')).exists():
                    raise ValidationError(
                        _('Public report type with this code name already exists'))
            else:
                organization_id = self.context['view'].kwargs.get('organization_pk')
                if ReportType.objects.filter(source__organization_id=organization_id,
                                             short_name=attrs.get('short_name')).exists():
                    raise ValidationError(
                        _('Report type with this code name already exists for organization '
                          '"{organization}"').
                        format(organization=Organization.objects.get(pk=organization_id))
                    )
        return result


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
            'value': obj.value
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
        fields = ('pk', 'created', 'organization', 'platform', 'report_type', 'system_created',
                  'user', 'owner_level')


class ImportBatchVerboseSerializer(ModelSerializer):

    user = UserSerializer(read_only=True)
    organization = OrganizationSerializer(read_only=True)
    platform = PlatformSerializer(read_only=True)
    report_type = ReportTypeSerializer(read_only=True)

    class Meta:
        model = ImportBatch
        fields = ('pk', 'created', 'organization', 'platform', 'report_type', 'system_created',
                  'user', 'owner_level', 'accesslog_count')


class ManualDataUploadSerializer(ModelSerializer):

    user = HiddenField(default=CurrentUserDefault())
    import_batch = ImportBatchSerializer(read_only=True)

    class Meta:
        model = ManualDataUpload
        fields = ('pk', 'report_type', 'organization', 'platform', 'data_file',
                  'user', 'created', 'is_processed', 'log', 'import_batch', 'extra')

