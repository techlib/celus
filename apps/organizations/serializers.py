from django.conf import settings
from rest_framework.fields import BooleanField
from rest_framework.serializers import ModelSerializer

from .models import Organization


class OrganizationSerializer(ModelSerializer):

    is_admin = BooleanField(read_only=True)
    is_member = BooleanField(read_only=True)

    class Meta:
        model = Organization
        fields = ('pk', 'ext_id', 'short_name', 'name', 'internal_id', 'ico', 'parent', 'is_admin',
                  'is_member') + tuple('name_'+lang[0] for lang in settings.LANGUAGES)
