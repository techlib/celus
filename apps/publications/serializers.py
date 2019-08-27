from rest_framework.fields import FloatField, JSONField
from rest_framework.serializers import ModelSerializer, IntegerField

from .models import Platform, Title


class PlatformSerializer(ModelSerializer):

    class Meta:
        model = Platform
        fields = ('pk', 'ext_id', 'short_name', 'name', 'provider', 'url')


class DetailedPlatformSerializer(ModelSerializer):

    title_count = IntegerField(read_only=True)
    interests = JSONField(read_only=True)
    rel_interest = FloatField(read_only=True)
    interest_title = IntegerField(read_only=True)

    class Meta:
        model = Platform
        fields = ('pk', 'ext_id', 'short_name', 'name', 'provider', 'url',
                  'title_count', 'interests', 'rel_interest', 'interest_title')


class PlatformSushiCredentialsSerializer(ModelSerializer):

    count = IntegerField(read_only=True, source='sushi_credentials_count')

    class Meta:
        model = Platform
        fields = ('pk', 'count')


class TitleSerializer(ModelSerializer):

    class Meta:
        model = Title
        fields = ('pk', 'name', 'pub_type', 'isbn', 'issn', 'eissn', 'doi')


class TitleCountSerializer(ModelSerializer):

    interest = IntegerField(read_only=True)

    class Meta:
        model = Title
        fields = ('pk', 'name', 'pub_type', 'isbn', 'issn', 'eissn', 'doi', 'interest')
