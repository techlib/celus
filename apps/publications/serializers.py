from core.models import DataSource
from organizations.models import Organization
from organizations.serializers import OrganizationSerializer
from rest_framework.exceptions import PermissionDenied
from rest_framework.fields import (
    BooleanField,
    CurrentUserDefault,
    DateTimeField,
    HiddenField,
    JSONField,
    SerializerMethodField,
    URLField,
)
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.serializers import IntegerField, ModelSerializer, Serializer

from .models import Platform, Title, TitleOverlapBatch


class SimplePlatformSerializer(ModelSerializer):
    class Meta:
        model = Platform
        fields = ('pk', 'ext_id', 'short_name', 'name', 'provider', 'url', 'counter_registry_id')


class DataSourceSerializer(ModelSerializer):
    organization = OrganizationSerializer()

    class Meta:
        model = DataSource
        fields = ('short_name', 'organization', 'type')


class PlatformSerializer(ModelSerializer):
    ext_id = IntegerField(read_only=True)
    source = DataSourceSerializer(read_only=True)

    class Meta:
        model = Platform
        fields = (
            'pk',
            'ext_id',
            'short_name',
            'name',
            'provider',
            'url',
            'knowledgebase',
            'source',
            'counter_registry_id',
        )


class AllPlatformSerializer(ModelSerializer):
    ext_id = IntegerField(read_only=True)
    source = DataSourceSerializer(read_only=True)
    has_raw_parser = BooleanField(read_only=True)

    class Meta:
        model = Platform
        fields = (
            'pk',
            'ext_id',
            'short_name',
            'name',
            'provider',
            'url',
            'knowledgebase',
            'source',
            'has_raw_parser',
            'counter_registry_id',
        )


class DetailedPlatformSerializer(ModelSerializer):

    title_count = IntegerField(read_only=True)
    interests = JSONField(read_only=True)
    has_data = BooleanField(read_only=True)

    class Meta:
        model = Platform
        fields = (
            'pk',
            'ext_id',
            'short_name',
            'name',
            'provider',
            'url',
            'title_count',
            'interests',
            'has_data',
            'counter_registry_id',
        )


class PlatformSushiCredentialsSerializer(ModelSerializer):

    count = IntegerField(read_only=True, source='sushi_credentials_count')

    class Meta:
        model = Platform
        fields = ('pk', 'count')


class TitleSerializer(ModelSerializer):

    pub_type_name = SerializerMethodField()

    class Meta:
        model = Title
        fields = ('pk', 'name', 'pub_type', 'isbn', 'issn', 'eissn', 'doi', 'pub_type_name')

    def get_pub_type_name(self, obj: Title):
        return obj.get_pub_type_display()


class TitleCountSerializer(ModelSerializer):

    interests = JSONField(read_only=True)
    platform_count = IntegerField(read_only=True)
    nonzero_platform_count = IntegerField(read_only=True)
    platform_ids = JSONField(read_only=True)
    pub_type_name = SerializerMethodField()
    total_interest = IntegerField(read_only=True)

    class Meta:
        model = Title
        fields = (
            'pk',
            'name',
            'pub_type',
            'isbn',
            'issn',
            'eissn',
            'doi',
            'interests',
            'pub_type_name',
            'platform_count',
            'nonzero_platform_count',
            'platform_ids',
            'total_interest',
        )

    def get_pub_type_name(self, obj: Title):
        return obj.get_pub_type_display()


class UseCaseSerializer(Serializer):

    url = URLField(required=True)
    organization = IntegerField(required=True)
    platform = IntegerField(required=True)
    counter_version = IntegerField(required=True)
    counter_report = IntegerField(required=True)
    latest = DateTimeField(required=True)
    count = IntegerField(required=True)


class TitleOverlapBatchSerializer(ModelSerializer):

    organization = OrganizationSerializer(read_only=True, required=False)

    class Meta:
        model = TitleOverlapBatch
        fields = (
            'pk',
            'organization',
            'created',
            'last_updated',
            'state',
            'source_file',
            'annotated_file',
            'processing_info',
        )


class TitleOverlapBatchCreateSerializer(TitleOverlapBatchSerializer):

    last_updated_by = HiddenField(default=CurrentUserDefault())
    organization = PrimaryKeyRelatedField(queryset=Organization.objects.all(), required=False)

    class Meta(TitleOverlapBatchSerializer.Meta):
        fields = TitleOverlapBatchSerializer.Meta.fields + ('last_updated_by',)

    def validate(self, attrs):
        result = super().validate(attrs)
        user = attrs['last_updated_by']
        if attrs.get('organization'):
            if not user.accessible_organizations().filter(pk=attrs['organization'].pk).exists():
                raise PermissionDenied('User does not have access to this organization')
        else:
            if (
                not user.is_superuser
                and not user.is_admin_of_master_organization
                and not user.is_user_of_master_organization
            ):
                raise PermissionDenied('User cannot set empty organization')
        return result


class DeleteAllDataPlatformSerializer(Serializer):
    delete_platform = BooleanField(required=False, default=False)
