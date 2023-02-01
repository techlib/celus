import logging

from django.conf import settings
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from .parsers import parse_changelog, parse_source_of_releases
from .serializers import ReleaseSerializer

logger = logging.getLogger(__name__)


class Releases(ViewSet):
    def list(self, request):
        parsed = parse_source_of_releases()
        if parsed:
            serializer = ReleaseSerializer(data=parsed, many=True)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.validated_data)
        else:
            return Response([])

    @action(detail=False, methods=['GET'])
    def latest(self, request):
        parsed = parse_source_of_releases()
        if parsed:
            latest_release = parsed[0]
            serializer = ReleaseSerializer(data=latest_release, required=False)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.validated_data)
        else:
            return Response({})


class ChangelogAPIView(APIView):
    def get(self, request):
        with open(settings.BASE_DIR / "CHANGELOG.md", 'rt', encoding='utf-8') as f:
            parsed_changelog = parse_changelog(f.read())
            return Response(parsed_changelog)
