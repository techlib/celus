from rest_framework.serializers import ModelSerializer

from logs.serializers import ReportTypeSimpleSerializer
from organizations.serializers import OrganizationSerializer
from publications.serializers import PlatformSerializer, TitleSerializer
from .models import Annotation


class AnnotationSerializer(ModelSerializer):

    organization = OrganizationSerializer(read_only=True)
    platform = PlatformSerializer(read_only=True)
    report_type = ReportTypeSimpleSerializer(read_only=True)
    title = TitleSerializer(read_only=True)

    class Meta:
        model = Annotation
        fields = ('pk', 'subject', 'short_message', 'message', 'start_date', 'end_date',
                  'organization', 'platform', 'report_type', 'title')
