from core.models import DataSource
from django.db import models
from rest_framework import filters


class PlatformFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if request.query_params.get('public_only', "").lower() == "true":
            queryset = queryset.filter(~models.Q(source__type=DataSource.TYPE_ORGANIZATION))
        return queryset
