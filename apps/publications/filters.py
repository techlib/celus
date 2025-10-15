from core.logic.type_conversion import to_bool
from core.models import DataSource
from django.db import models
from events.models import Event
from rest_framework import filters
from rest_framework.exceptions import ValidationError


class PlatformFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if request.query_params.get("public_only", "").lower() == "true":
            queryset = queryset.filter(~models.Q(source__type=DataSource.TYPE_ORGANIZATION))

        if has_event_str := request.GET.get("has_event"):
            has_event = to_bool(has_event_str)
            fltr = models.Exists(Event.objects.filter(platform_id=models.OuterRef("pk")))
            queryset = queryset.filter(fltr if has_event else ~fltr)

        return queryset


class PubTypeFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if pub_type := request.GET.get("pub_type"):
            queryset = queryset.filter(pub_type=pub_type)
        return queryset


class HasWhiteListedIrReportFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        whitelisted_ir = request.query_params.get("whitelisted_ir", "").lower().strip()
        if whitelisted_ir not in ["true", "false", ""]:
            raise ValidationError({"whitelisted_ir": f"unknown value '{whitelisted_ir}'"})

        if whitelisted_ir:
            queryset = queryset.filter(
                knowledgebase__providers__contains=[
                    {
                        "assigned_report_types": [
                            {"whitelisted": whitelisted_ir == "true", "report_type": "IR"}
                        ]
                    }
                ]
            )

        return queryset
