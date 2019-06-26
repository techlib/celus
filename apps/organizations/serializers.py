from rest_framework.serializers import ModelSerializer

from .models import Organization


class OrganizationSerializer(ModelSerializer):

    class Meta:
        model = Organization
        fields = ('pk', 'ext_id', 'short_name', 'name', 'internal_id', 'ico', 'parent')
