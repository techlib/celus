from rest_framework.fields import (
    CharField,
    ListField,
    JSONField,
    SerializerMethodField,
    BooleanField,
)
from rest_framework.serializers import ModelSerializer, IntegerField

from .models import Platform, Title


class PlatformSerializer(ModelSerializer):
    class Meta:
        model = Platform
        fields = ('pk', 'ext_id', 'short_name', 'name', 'provider', 'url', 'knowledgebase')


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


class PlatformKnowledgebaseSerializer(ModelSerializer):
    knowledgebase = JSONField(read_only=True)

    class Meta:
        model = Platform
        fields = ("knowledgebase",)
