from core.logic.type_conversion import to_bool
from rest_framework import filters


class ImportanceFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if importance := request.query_params.get("importance", ""):
            queryset = queryset.filter(importance=importance)
        return queryset


class CategoryFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if category := request.query_params.get("category", ""):
            queryset = queryset.filter(category=category)
        return queryset


class ReadStatusFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if read := request.query_params.get("read", ""):
            queryset = queryset.filter(read=to_bool(read))
        return queryset
