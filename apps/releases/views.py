import logging

from releases.logic.releases import add_dates_to_releases_from_changelog, get_releases_entries
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from .logic.changelog import get_changelog_entries
from .serializers import ReleaseSerializer

logger = logging.getLogger(__name__)


class Releases(ViewSet):
    def list(self, request):
        parsed = get_releases_entries()
        if parsed:
            add_dates_to_releases_from_changelog(parsed, get_changelog_entries())
            serializer = ReleaseSerializer(data=parsed, many=True)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.validated_data)
        else:
            return Response([])

    @action(detail=False, methods=['GET'])
    def latest(self, request):
        parsed = get_releases_entries()
        if parsed:
            latest_release = parsed[0]
            add_dates_to_releases_from_changelog([latest_release], get_changelog_entries())
            serializer = ReleaseSerializer(data=latest_release, required=False)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.validated_data)
        else:
            return Response({})


class ChangelogAPIView(APIView):
    def get(self, request):
        return Response(get_changelog_entries())
