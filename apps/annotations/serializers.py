from django.utils.log import RequireDebugFalse
from rest_framework.fields import ReadOnlyField
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.serializers import ModelSerializer

from organizations.models import Organization
from organizations.serializers import OrganizationSerializer
from publications.models import Platform
from publications.serializers import PlatformSerializer
from .models import Annotation


class AnnotationSerializer(ModelSerializer):

    organization = OrganizationSerializer(read_only=True)
    platform = PlatformSerializer(read_only=True)
    subject = ReadOnlyField()
    organization_id = PrimaryKeyRelatedField(source='organization', write_only=True,
                                             allow_null=True, queryset=Organization.objects.all())
    platform_id = PrimaryKeyRelatedField(source='platform', write_only=True, allow_null=True,
                                         queryset=Platform.objects.all())

    class Meta:
        model = Annotation
        fields = ('pk', 'organization_id', 'platform_id',
                  'subject', 'subject_en', 'subject_cs',
                  'short_message', 'short_message_en', 'short_message_cs',
                  'message', 'message_en', 'message_cs',
                  'start_date', 'end_date', 'organization', 'platform', 'level')
        extra_kwargs = {
            'subject_en': {'allow_blank': False},
            'subject_cs': {'allow_blank': False},
        }

