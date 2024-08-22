from core.filters import PkMultiValueFilterBackend
from rest_framework import filters


class AccessibleFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if not request.user.is_user_of_master_organization:
            queryset = queryset.filter(organization__in=request.user.accessible_organizations())
        return queryset


class ModifiableFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if not request.user.is_admin_of_master_organization:
            queryset = queryset.filter(organization__in=request.user.accessible_organizations())
        return queryset


class UserFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if user := request.GET.get("user"):
            queryset = queryset.filter(user_id=user)
        return queryset


class OrderByFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        order_by = request.GET.get("order_by", "created")
        if request.GET.get("desc") in ("true", 1):
            order_by = "-" + order_by
        # ensure that pk is always part of ordering to ensure stable ordering in case of same values
        order_by = [order_by, "pk"]
        return queryset.order_by(*order_by)


class DimensionFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if dimension_id := request.GET.get("dimension"):
            queryset = queryset.filter(dimension_id=dimension_id)
        return queryset


class PrimaryDimensionFlexiReportFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if primary_dimension := request.GET.get("primary_dimension"):
            queryset = queryset.filter(report_config__primary_dimension=primary_dimension)
        return queryset


class MultiPlatformFilter(PkMultiValueFilterBackend):
    filter_field = "platform_id"
    query_param = "platform_ids"


class MultiReportTypeFilter(PkMultiValueFilterBackend):
    filter_field = "report_type_id"
    query_param = "report_type_ids"
