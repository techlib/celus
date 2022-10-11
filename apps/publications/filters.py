from rest_framework import filters
from django.db import models
from core.models import DataSource


class PlatformFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if request.query_params.get('public_only', "").lower() == "true":
            queryset = queryset.filter(~models.Q(source__type=DataSource.TYPE_ORGANIZATION))
        return queryset
