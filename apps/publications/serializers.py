from rest_framework.fields import FloatField
from rest_framework.serializers import ModelSerializer, IntegerField

from .models import Platform, Title


class PlatformSerializer(ModelSerializer):

    class Meta:
        model = Platform
        fields = ('pk', 'ext_id', 'short_name', 'name', 'provider', 'url')


class DetailedPlatformSerializer(ModelSerializer):

    title_count = IntegerField(read_only=True)
    interest = IntegerField(read_only=True)
    rel_interest = FloatField(read_only=True)
    title_interest = IntegerField(read_only=True)

    class Meta:
        model = Platform
        fields = ('pk', 'ext_id', 'short_name', 'name', 'provider', 'url',
                  'title_count', 'interest', 'rel_interest', 'title_interest')


class TitleSerializer(ModelSerializer):

    class Meta:
        model = Title
        fields = ('pk', 'name', 'pub_type', 'isbn', 'issn', 'eissn', 'doi')


class TitleCountSerializer(ModelSerializer):

    count = IntegerField(read_only=True)

    class Meta:
        model = Title
        fields = ('pk', 'name', 'pub_type', 'isbn', 'issn', 'eissn', 'doi', 'count')
