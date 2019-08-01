from django.conf import settings
from rest_framework.serializers import ModelSerializer

from .models import Organization


class OrganizationSerializer(ModelSerializer):

    class Meta:
        model = Organization
        fields = ('pk', 'ext_id', 'short_name', 'name', 'internal_id', 'ico', 'parent',
                  ) + tuple('name_'+lang[0] for lang in settings.LANGUAGES)
