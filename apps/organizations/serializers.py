from django.conf import settings
from rest_framework.fields import BooleanField, CharField
from rest_framework.serializers import ModelSerializer

from .models import Organization


class OrganizationSerializer(ModelSerializer):

    is_admin = BooleanField(read_only=True)
    is_member = BooleanField(read_only=True)

    class Meta:
        model = Organization
        fields = (
            'pk',
            'ext_id',
            'short_name',
            'name',
            'internal_id',
            'ico',
            'parent',
            'is_admin',
            'is_member',
            'is_raw_data_import_enabled',
        ) + tuple('name_' + lang[0] for lang in settings.LANGUAGES)


class OrganizationSimpleSerializer(ModelSerializer):
    name = CharField(max_length=100)

    class Meta:
        model = Organization
        fields = ('name', 'url')


class OrganizationShortSerializer(ModelSerializer):
    class Meta:
        model = Organization
        fields = ('pk', 'short_name', 'name')
