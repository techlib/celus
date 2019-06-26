from rest_framework.serializers import ModelSerializer

from .models import Platform, Title


class PlatformSerializer(ModelSerializer):

    class Meta:
        model = Platform
        fields = ('pk', 'ext_id', 'short_name', 'name', 'provider', 'url')


class TitleSerializer(ModelSerializer):

    class Meta:
        model = Title
        fields = ('pk', 'name', 'pub_type', 'isbn', 'issn', 'eissn', 'doi')
