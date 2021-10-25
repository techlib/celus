import dateparser
from distutils.util import strtobool

from django.shortcuts import get_object_or_404
from django.db.models import F, Q
from rest_framework import filters

from sushi.models import AttemptStatus


class OrganizationFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        organizations = request.user.accessible_organizations()

        organization = request.query_params.get("organization", "")
        if organization and organization != "-1":
            credentials_organization = get_object_or_404(organizations, pk=organization)
            queryset = queryset.filter(credentials__organization=credentials_organization)
        else:
            queryset = queryset.filter(credentials__organization__in=organizations)
        return queryset


class PlatformFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        platform = request.query_params.get("platform", "")
        if platform:
            queryset = queryset.filter(credentials__platform_id=platform)
        return queryset


class ReportFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        report = request.query_params.get("report", "")
        if report:
            queryset = queryset.filter(counter_report_id=report)
        return queryset


class DateFromFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        date_from = dateparser.parse(request.query_params.get("date_from", ""))
        if date_from:
            queryset = queryset.filter(attempt__timestamp__date__gte=date_from)
        return queryset


class MonthFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        month = dateparser.parse(request.query_params.get("month", ""))
        if month:
            queryset = queryset.filter(start_date__gte=month)
            queryset = queryset.filter(end_date__lte=month)
        return queryset


class CounterVersionFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        counter_version = request.query_params.get("counter_version", "")
        if counter_version:
            queryset = queryset.filter(credentials__counter_version=counter_version)
        return queryset


class ModeFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        mode = request.query_params.get('mode', "")
        if mode == 'success_and_current':
            queryset = queryset.filter(
                Q(attempt__credentials_version_hash=F('credentials__version_hash'))
                | Q(attempt__status__in=AttemptStatus.successes())
            )
        elif mode == 'current':
            queryset = queryset.filter(
                attempt__credentials_version_hash=F('credentials__version_hash'),
            )
        return queryset


class AttemptFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        try:
            attempt = bool(strtobool(request.query_params.get('attempt', '')))
            queryset = queryset.filter(attempt__isnull=not attempt)
        except ValueError:
            pass

        return queryset


class OrderingFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        order_by = request.query_params.get('order_by', "")
        if order_by in ['timestamp', 'error_code']:
            order_by = f"attempt__{order_by}"
        desc = request.query_params.get('desc', 'false')
        if order_by:
            prefix = '-' if desc == 'true' else ''
            queryset = queryset.order_by(prefix + order_by)
        return queryset


class CredentialsFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        credentials = request.query_params.get("credentials", "")
        if credentials:
            queryset = queryset.filter(credentials_id=credentials)
        return queryset
