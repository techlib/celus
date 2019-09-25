from rest_framework.serializers import ModelSerializer

from organizations.serializers import OrganizationSerializer
from publications.serializers import PlatformSerializer
from .models import Annotation


class AnnotationSerializer(ModelSerializer):

    organization = OrganizationSerializer(read_only=True)
    platform = PlatformSerializer(read_only=True)

    class Meta:
        model = Annotation
        fields = ('pk', 'subject', 'short_message', 'message', 'start_date', 'end_date',
                  'organization', 'platform', 'level')
