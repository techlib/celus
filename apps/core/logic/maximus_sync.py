import logging

import requests
from django.conf import settings
from organizations.models import Organization, UserOrganization
from rest_framework import serializers

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


def get_organizations():
    return CelusOrganizationSerializer(Organization.objects.all(), many=True).data


def get_users():
    return CelusUserSerializer(User.objects.all(), many=True).data


def get_relations():
    return CelusUserOrganizationSerializer(UserOrganization.objects.all(), many=True).data


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
    }
    for k, v in d.items():
        c.post(settings.MAXIMUS_URL + k, json=v).raise_for_status()
