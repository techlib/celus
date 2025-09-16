from enum import Enum

from core.logic.type_conversion import to_bool
from django.conf import settings
from django.db.models import Q
from rest_framework import filters


class PotentialIssues(str, Enum):
    BROKEN = "broken"
    NOT_VALIDATED = "not_validated"
    CAN_UPDATE_VERIFIED = "can_update_verified"
    CAN_UPDATE = "can_update"
    DUPLICATED = "duplicated"


class CredentialsPlatformFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if getattr(view, "_suppress_platform_filter", False):
            return queryset

        platform = request.query_params.get("platform", "")
        if platform:
            queryset = queryset.filter(platform_id=platform)
        return queryset


class CredentialsCounterVersionFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        counter_version = request.query_params.get("counter_version", "")
        if counter_version:
            queryset = queryset.filter(counter_version=counter_version)
        return queryset


class CredentialsLastHarvestableMonthFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        lhm = request.query_params.get("last_harvestable_month", "")
        if lhm:
            is_null = not to_bool(lhm)
            queryset = queryset.filter(last_harvestable_month__isnull=is_null)
        return queryset


class CredentialsPotentialIssuesFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        pi = request.query_params.get("potential_issues", "")

        if pi == PotentialIssues.BROKEN:
            queryset = queryset.filter(any_broken=True)
        elif pi == PotentialIssues.NOT_VALIDATED:
            queryset = queryset.annotate_verified().filter(verified=False)
        elif pi == PotentialIssues.CAN_UPDATE_VERIFIED:
            queryset = queryset.filter(can_update=True, has_51_provider=True)
        elif pi == PotentialIssues.CAN_UPDATE:
            queryset = queryset.filter(can_update=True)
        elif pi == PotentialIssues.DUPLICATED:
            if settings.CONSORTIAL_INSTALLATION:
                queryset = queryset.filter(Q(same_global__gt=1))
            else:
                queryset = queryset.filter(Q(same_in_org__gt=1))

        return queryset


class CredentialsEnabledFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        enabled_str = request.query_params.get("enabled", "")
        if enabled_str:
            enabled = to_bool(enabled_str)
            queryset = queryset.filter(enabled=enabled)
        return queryset
