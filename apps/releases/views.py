import logging

from django.conf import settings
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from .releases_parser import parse_source_of_releases
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


class Changelog(ViewSet):
    def list(self, request):
        with open(settings.BASE_DIR / "CHANGELOG.md") as f:
            content = f.read()
            list_of_releases = content.split("## [")
            list_of_releases.pop(0)
            parsed_changelog = []
            for release in list_of_releases:
                rel_parts = release.split("\n\n", 1)
                rel_dict = {
                    "version": rel_parts[0].rstrip("]"),
                    "markdown": rel_parts[1],
                }
                parsed_changelog.append(rel_dict)
            return Response(parsed_changelog)
