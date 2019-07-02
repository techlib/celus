from rest_framework.serializers import ModelSerializer, IntegerField

from .models import Platform, Title


class PlatformSerializer(ModelSerializer):

    class Meta:
        model = Platform
        fields = ('pk', 'ext_id', 'short_name', 'name', 'provider', 'url')


class DetailedPlatformSerializer(ModelSerializer):

    title_count = IntegerField(read_only=True)

    class Meta:
        model = Platform
        fields = ('pk', 'ext_id', 'short_name', 'name', 'provider', 'url', 'title_count')


class TitleSerializer(ModelSerializer):

    class Meta:
        model = Title
        fields = ('pk', 'name', 'pub_type', 'isbn', 'issn', 'eissn', 'doi')
