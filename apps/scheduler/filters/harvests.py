import dateparser
from distutils.util import strtobool

from django.shortcuts import get_object_or_404
from django.db.models import F, Q
from rest_framework import filters

from core.logic.dates import parse_month, month_end


class FinishedFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        finished = request.query_params.get("finished", "")
        if finished == "yes":
            queryset = queryset.filter(planned=0)
        elif finished == "no":
            queryset = queryset.filter(planned__gt=0)
        elif finished == "working":
            queryset = queryset.filter(working__gt=0)
        return queryset


class BrokenFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if broken := request.query_params.get('broken', None):
            if strtobool(broken):
                queryset = queryset.filter(broken__gt=0)
            else:
                queryset = queryset.filter(broken=0)
        return queryset


class PlatformsFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if platforms := request.query_params.get('platforms', None):
            platforms = platforms.strip()
            if platforms:
                queryset = queryset.filter(
                    intentions__credentials__platform__pk__in=platforms.split(",")
                )
        return queryset


class AutomaticFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if automatic := request.query_params.get('automatic', None):
            if strtobool(automatic):
                queryset = queryset.filter(automatic__isnull=False)
            else:
                queryset = queryset.filter(automatic__isnull=True)

        return queryset


class MonthFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if month := request.query_params.get('month', None):
            parsed_month = parse_month(month)
            queryset = queryset.filter(start_date__lte=parsed_month, end_date__gte=parsed_month)

        return queryset


class OrderingFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        order_by = request.query_params.get('order_by', '')
        desc = strtobool(request.query_params.get('desc', 'false'))
        if order_by:
            if order_by not in (
                'created',
                'pk',
                'automatic',
                'finished',
                'last_attempt_date',
                'attempt_count',
                'start_date',
                'last_processed',
            ):
                order_by = 'pk'
            order_desc = "desc" if desc else "asc"
            queryset = queryset.order_by(getattr(F(order_by), order_desc)(nulls_last=True))

        return queryset