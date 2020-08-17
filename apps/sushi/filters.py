from rest_framework.compat import coreapi, coreschema
from rest_framework.filters import BaseFilterBackend
from rest_framework.permissions import SAFE_METHODS

from .serializers import SushiCleanupSerializer


class CleanupFilterBackend(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        serializer = SushiCleanupSerializer(
            data=request.query_params if request.method in SAFE_METHODS else request.data
        )

        # filter only if older_than is set and contains a propper value
        serializer.is_valid(raise_exception=True)

        older_than = serializer.validated_data.get('older_than')
        if older_than:
            queryset = queryset.filter(last_updated__lt=older_than)
        return queryset
