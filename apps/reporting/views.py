import logging
from copy import deepcopy

from core.logic.dates import month_end, parse_month
from core.validators import month_validator
from django.conf import settings
from django.http import HttpResponse
from organizations.models import Organization
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .logic.anomalies import AnomalyDetector, AnomalySource
from .logic.computation import Report
from .logic.export import XlsxExporter
from .logic.report_definitions import REPORTS, get_report_def_by_name
from .serializers import AnomalyDetailsSerializer, AnomalySerializer, ReportSerializer

logger = logging.getLogger(__name__)


def localize_report_definition(report_def, lang):
    """
    Create a copy of the report definition dictionary where potentially localized strings are
    replaced with the strings in the given language.
    """
    report_def = deepcopy(report_def)
    for key in ["description", "name", "explanation"]:
        if isinstance(report_def.get(key), dict):
            report_def[key] = report_def[key][lang]
    for part in report_def["parts"]:
        for key in ["name", "description", "explanation"]:
            if isinstance(part.get(key), dict):
                part[key] = part[key][lang]
        for stage in part["stages"]:
            if isinstance(stage.get("name"), dict):
                stage["name"] = stage["name"][lang]
    return report_def


def visible_reports(request):
    show_preview = settings.SHOW_PREVIEW_SPECIALIZED_REPORTS and (
        request.user.is_superuser or request.user.is_admin_of_master_organization
    )
    return [rep for rep in REPORTS if not rep.get("preview", False) or show_preview]


class ReportListView(APIView):
    def get(self, request):
        # we deserialize the reports to make sure they are valid and then serialize them again
        # it also fills in the default values, like names and ids when they are not explicitly set
        # first we deal with possible translations in the report definitions
        lang = request.user.language
        if lang not in [rec[0] for rec in settings.AVAILABLE_LANGUAGES]:
            lang = settings.AVAILABLE_LANGUAGES[0][0]
        reports = [
            Report.from_dict(localize_report_definition(rep, lang))
            for rep in visible_reports(request)
        ]
        serializer = ReportSerializer(reports, many=True)
        return Response(serializer.data)


class ReportDataView(APIView):
    class ParamSerializer(serializers.Serializer):
        start_date = serializers.CharField(validators=[month_validator], required=True)
        end_date = serializers.CharField(validators=[month_validator], required=True)
        organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all())

    def create_report(self, report_name, lang) -> Report:
        report_def = get_report_def_by_name(report_name)
        if report_def is None:
            raise NotFound(f'Report with name "{report_name}" not found')
        return Report.from_dict(localize_report_definition(report_def, lang))

    def get_params(self, request) -> dict:
        param_ser = self.ParamSerializer(data=request.query_params)
        param_ser.is_valid(raise_exception=True)
        if (
            not request.user.accessible_organizations()
            .filter(pk=param_ser.validated_data["organization"].pk)
            .exists()
        ):
            raise PermissionDenied(
                {"error": "User is not allowed to access the selected organization"}
            )
        data = dict(param_ser.validated_data)
        data["start_date"] = parse_month(data["start_date"])
        data["end_date"] = month_end(parse_month(data["end_date"]))
        return data

    def get(self, request, report_name):
        report = self.create_report(report_name, request.LANGUAGE_CODE)
        params = self.get_params(request)
        report.retrieve_data(**params)
        out = report.get_output(as_dicts=True)
        return Response(out)


class ReportExportView(ReportDataView):
    def get(self, request, report_name):
        report = self.create_report(report_name, request.LANGUAGE_CODE)
        params = self.get_params(request)
        report.retrieve_data(**params)
        exporter = XlsxExporter(report)
        export_data = exporter.export()
        return HttpResponse(
            export_data,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{report.name}.xlsx"'},
        )


class AnomalyReportView(APIView):
    def check_clickhouse_active(self, request: Request) -> None:
        if not getattr(request, "USE_CLICKHOUSE", False):
            raise NotFound(detail="This API endpoint requires ClickHouse integration to be active.")

    def get(self, request: Request) -> Response:
        self.check_clickhouse_active(request)
        month = request.query_params.get("month")
        month_to = request.query_params.get("month_to")
        organization_id = request.query_params.get("organization")

        if not month or not month_to:
            raise ValidationError('Missing "month" or "month_to" URL param')

        cutoff_date = parse_month(month)  # first day of the first month
        cutoff_date_to = parse_month(month_to)  # first day of the last month
        cutoff_date_str = cutoff_date.strftime("%Y-%m-%d")
        cutoff_date_to_str = cutoff_date_to.strftime("%Y-%m-%d")

        # Build allowed organization filter: if org param provided, validate; otherwise
        # use all accessible orgs for the user
        if organization_id:
            # allow only if within accessible orgs
            if not request.user.accessible_organizations().filter(pk=organization_id).exists():
                raise PermissionDenied("Organization not accessible")
            org_ids = [int(organization_id)]
        else:
            org_ids = list(request.user.accessible_organizations().values_list("pk", flat=True))

        anomaly_detector = AnomalyDetector(cutoff_date_str, cutoff_date_to_str, org_ids)
        # Fetch anomalies with history (reasons fetched separately on expand)
        res_rows = anomaly_detector.get_anomalies()
        serializer = AnomalySerializer(res_rows, many=True)
        return Response(serializer.data)


class AnomalyDetailsView(APIView):
    def check_clickhouse_active(self, request: Request) -> None:
        if not getattr(request, "USE_CLICKHOUSE", False):
            raise NotFound(detail="This API endpoint requires ClickHouse integration to be active.")

    def get(self, request: Request) -> Response:
        self.check_clickhouse_active(request)

        month = request.query_params.get("month")
        organization_id = request.query_params.get("organization")
        platform_id = request.query_params.get("platform")
        report_type_id = request.query_params.get("report_type")
        metric_id = request.query_params.get("metric")

        if not all([month, organization_id, platform_id, report_type_id, metric_id]):
            raise ValidationError(
                "Missing required params: month, organization, platform, report_type, metric"
            )

        # Validate organization access
        if not request.user.accessible_organizations().filter(pk=organization_id).exists():
            raise PermissionDenied("Organization not accessible")

        cutoff_date_str = parse_month(month).strftime("%Y-%m-%d")

        # We compute details using a single-month window (month == month_to)
        anomaly_detector = AnomalyDetector(cutoff_date_str, cutoff_date_str, [int(organization_id)])

        res = anomaly_detector.get_anomaly_details(
            AnomalySource(
                anomaly_id=1,
                anomaly_date=cutoff_date_str,
                platform_id=int(platform_id),
                organization_id=int(organization_id),
                report_type_id=int(report_type_id),
                metric_id=int(metric_id),
            )
        )

        serializer = AnomalyDetailsSerializer(res)
        return Response(serializer.data)
