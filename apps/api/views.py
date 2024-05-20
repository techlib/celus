import uuid

from core.logic.dates import parse_month
from core.validators import month_validator
from django.db.models import Sum
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from export.models import FlexibleDataAPIExport
from export.serializers import FlexibleDataAPIExportSerializer
from export.tasks import process_flexible_api_export_task
from hcube.api.models.aggregation import Sum as HSum
from hcube.api.models.transforms import StoredMap
from logs.cubes import AccessLogCube, ch_backend
from logs.logic.queries import find_best_materialized_view
from logs.models import AccessLog, DimensionText, ReportType
from publications.models import Platform, Title
from rest_framework.fields import BooleanField, CharField, ListField
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from scheduler.models import FetchIntention
from sushi.models import SushiCredentials, SushiFetchAttempt

from api.auth import extract_org_from_request_api_key
from api.permissions import HasOrganizationAPIKey
from api.throttling import APIKeyBasedThrottle


class RedocView(TemplateView):
    template_name = "api/redoc.html"


class PlatformReportView(APIView):
    class ParamSerializer(Serializer):
        month = CharField(validators=[month_validator], required=True)
        dims = CharField(required=True, allow_blank=True)

    class OutputSerializer(Serializer):
        records = ListField(default=list)
        status = CharField()
        complete_data = BooleanField(default=False)

    permission_classes = [HasOrganizationAPIKey]
    throttle_classes = [APIKeyBasedThrottle]

    def get(self, request, report_type, platform_id):
        organization = extract_org_from_request_api_key(self.request)
        if not organization:
            # we should not get here as the permission_classes should take care of it
            # but this is a guard just in case
            return HttpResponseBadRequest(
                "API key authentication not successful - "
                "you may be missing the api key in the Authorization header"
            )
        param_serializer = self.ParamSerializer(data=request.GET)
        param_serializer.is_valid(raise_exception=True)

        rt = get_object_or_404(ReportType.objects.all(), short_name=report_type)
        month_date = parse_month(param_serializer.validated_data["month"])
        # dimensions
        current_dim_names = {dim.short_name for dim in rt.dimensions_sorted}
        req_dims_str = param_serializer.validated_data["dims"]
        req_dims = set(req_dims_str.split("|")) if req_dims_str else set()
        if not req_dims.issubset(current_dim_names):
            unknown_dims = "|".join(req_dims - current_dim_names)
            all_dims = "|".join(current_dim_names)
            return HttpResponseBadRequest(
                f"Unknown dimensions for this report type: {unknown_dims}. "
                f"Valid dimensions are: {all_dims}"
            )
        reported_dims = [
            f"dim{i+1}" for i, dim in enumerate(rt.dimensions_sorted) if dim.short_name in req_dims
        ]
        # deal with possible uuid being used as platform_id
        if isinstance(platform_id, uuid.UUID):
            platform_id = get_object_or_404(
                Platform.objects.all(), counter_registry_id=platform_id
            ).pk

        if request.USE_CLICKHOUSE:
            query = AccessLogCube.query().filter(
                report_type_id=rt.pk,
                platform_id=platform_id,
                date=month_date,
                organization_id=organization.pk,
            )
            data = (
                {
                    # make the data look the same as the non-clickhouse version
                    "metric__short_name": rec.metric_short_name,
                    "target": rec.target_id,
                    **rec._asdict(),
                }
                for rec in ch_backend.get_records(
                    query.group_by("target_id", "metric_id", *reported_dims)
                    .aggregate(hits=HSum("value"))
                    .transform(metric_short_name=StoredMap("metric_id", "metric", "short_name"))
                )
            )
            title_ids = {
                rec.target_id for rec in ch_backend.get_records(query.group_by("target_id"))
            }

        else:
            # possibly replace the report type with a materialized version
            used_rt = find_best_materialized_view(rt, ["target", "metric", *reported_dims]) or rt
            qs = AccessLog.objects.filter(
                report_type=used_rt,
                platform_id=platform_id,
                date=month_date,
                organization=organization,
            )
            data = qs.values("target", "metric__short_name", *reported_dims).annotate(
                hits=Sum("value")
            )
            title_ids = qs.values_list("target_id", flat=True).distinct()

        text_id_to_text = {
            dt["id"]: dt["text"]
            for dt in DimensionText.objects.filter(dimension__report_types=rt).values("id", "text")
        }
        out = []
        title_fields = {
            "name": "title",
            "isbn": "isbn",
            "issn": "issn",
            "eissn": "eissn",
            "doi": "doi",
        }
        titles = {
            t["pk"]: t
            for t in Title.objects.filter(pk__in=title_ids).values("pk", *title_fields.keys())
        }
        for al in data:
            rec = {"hits": al["hits"], "metric": al["metric__short_name"]}
            for i, dim in enumerate(rt.dimensions_sorted):
                key = f"dim{i + 1}"
                if key in al:
                    value = al[key]
                    rec[dim.short_name] = text_id_to_text.get(value, value)
            title_id = al["target"]
            if title_id:
                title = titles[title_id]
                for src, target in title_fields.items():
                    rec[target] = title[src]
            out.append(rec)

        if len(out) == 0:
            # there are no records there, we need to find out why
            try:
                relevant_sushi = SushiCredentials.objects.get(
                    platform_id=platform_id,
                    organization=organization,
                    counter_reports__report_type=rt,
                )
            except SushiCredentials.DoesNotExist:
                return self._get_response(
                    {"status": "SUSHI credentials not present for this report"}
                )
            # there is some sushi related to this report
            # check if credentials are active
            if not relevant_sushi.enabled:
                return self._get_response(
                    {"status": "SUSHI credentials are not automatically harvested"}
                )
            elif relevant_sushi.broken:
                return self._get_response({"status": "SUSHI credentials are incorrect"})
            # check if the report was marked as broken for current credentials
            report_to_credentials = relevant_sushi.counterreportstocredentials_set.get(
                counter_report__report_type=rt
            )
            if report_to_credentials.broken:
                return self._get_response(
                    {"status": "Report marked as broken for existing credentials"}
                )
            # we have active credentials, let's check the attempts
            fetch_attempts = SushiFetchAttempt.objects.filter(
                credentials=relevant_sushi,
                counter_report__report_type=rt,
                start_date__lte=month_date,
                end_date__gte=month_date,
            ).order_by("-last_updated")
            if not fetch_attempts:
                return self._get_response({"status": "Data not yet harvested"})
            last: SushiFetchAttempt = fetch_attempts[0]
            # before checking the intention, make sure it exists
            try:
                fi = last.fetchintention
            except FetchIntention.DoesNotExist:
                pass
            else:
                if fi != fi.queue.end:  # not last in queue
                    return self._get_response({"status": "Harvesting ongoing"})
            if last.error_code == "3030":
                return self._get_response(
                    {"records": out, "complete_data": True, "status": "Empty data"}
                )
            return self._get_response({"status": "Harvesting error"})

        return self._get_response({"records": out, "status": "OK", "complete_data": True})

    def _get_response(self, data):
        output_serializer = self.OutputSerializer(data=data)
        output_serializer.is_valid(raise_exception=True)
        return Response(output_serializer.data)


class FlexibleDataAPIExportViewSet(ModelViewSet):
    queryset = FlexibleDataAPIExport.objects.none()
    serializer_class = FlexibleDataAPIExportSerializer

    permission_classes = [HasOrganizationAPIKey]
    throttle_classes = [APIKeyBasedThrottle]

    def get_queryset(self):
        organization = extract_org_from_request_api_key(self.request)
        if not organization:
            # we should not get here as the permission_classes should take care of it
            # but this is a guard just in case
            return HttpResponseBadRequest(
                "API key authentication not successful - "
                "you may be missing the api key in the Authorization header"
            )
        return FlexibleDataAPIExport.objects.filter(owner_org=organization).order_by("-created")

    def perform_create(self, serializer):
        export = serializer.save()
        process_flexible_api_export_task.apply_async(args=(export.pk,), countdown=2)
