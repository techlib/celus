import logging

import requests
from django.conf import settings
from organizations.models import Organization, UserOrganization
from publications.models import Platform
from rest_framework import serializers
from sushi.models import SushiCredentials

from ..models import User

logger = logging.getLogger(__name__)


class CelusUserSerializer(serializers.ModelSerializer):
    ext_id = serializers.IntegerField(source='id')

    class Meta:
        model = User
        fields = (
            'ext_id',
            'username',
            'first_name',
            'last_name',
            'email',
            'date_joined',
            'last_login',
        )


class CelusOrganizationSerializer(serializers.ModelSerializer):
    ext_id = serializers.IntegerField(source='id')

    class Meta:
        model = Organization
        fields = (
            'ext_id',
            'name',
            'short_name',
            'raw_data_import_enabled',
        )


class CelusUserOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserOrganization
        fields = (
            'user',
            'organization',
            'is_admin',
        )


class CallableRelatedField(serializers.SlugRelatedField):
    def to_representation(self, obj):
        return getattr(obj, self.slug_field)()


class CelusPlatformSerializer(serializers.ModelSerializer):
    ext_id = serializers.IntegerField(source='id')
    source = serializers.StringRelatedField()
    source_type = CallableRelatedField(
        read_only=True,
        slug_field='get_type_display',
        source='source',
    )

    class Meta:
        model = Platform
        fields = (
            'ext_id',
            'short_name',
            'name',
            'source',
            'source_type',
            'counter_registry_id',
        )


class SushiCredentialsSerializer(serializers.ModelSerializer):
    ext_id = serializers.IntegerField(source='id')
    counter_reports = serializers.SlugRelatedField(
        many=True,
        slug_field='code',
        read_only=True,
    )
    verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = SushiCredentials
        fields = (
            'ext_id',
            'organization',
            'platform',
            'url',
            'counter_version',
            'requestor_id',
            'customer_id',
            'http_username',
            'http_password',
            'api_key',
            'extra_params',
            'enabled',
            'counter_reports',
            'outside_consortium',
            'lock_level',
            'broken',
            'verified',
        )


def get_organizations():
    return CelusOrganizationSerializer(Organization.objects.all(), many=True).data


def get_users():
    return CelusUserSerializer(User.objects.all(), many=True).data


def get_relations():
    return CelusUserOrganizationSerializer(UserOrganization.objects.all(), many=True).data


def get_platforms():
    return CelusPlatformSerializer(
        Platform.objects.all().select_related('source', 'source__organization'), many=True
    ).data


def get_sushi_credentials():
    return SushiCredentialsSerializer(
        SushiCredentials.objects.all().prefetch_related('counter_reports').annotate_verified(),
        many=True,
    ).data


def sync():
    if not settings.MAXIMUS_URL or not settings.MAXIMUS_TOKEN:
        logger.warning("MAXIMUS_URL/MAXIMUS_TOKEN not set - not syncing")
        return

    c = requests.session()
    c.headers['Authorization'] = 'Api-Key ' + settings.MAXIMUS_TOKEN
    d = {
        '/organizations/': get_organizations(),
        '/users/': get_users(),
        '/users-organizations/': get_relations(),
        '/platforms/': get_platforms(),
        '/sushi-credentials/': get_sushi_credentials(),
    }
    for k, v in d.items():
        c.post(settings.MAXIMUS_URL + k, json=v).raise_for_status()
