from copy import deepcopy

from core.logic.dates import month_end, parse_month
from core.validators import month_validator
from django.conf import settings
from django.http import HttpResponse
from organizations.models import Organization
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .logic.computation import Report
from .logic.export import XlsxExporter
from .logic.report_definitions import REPORTS, get_report_def_by_name
from .serializers import ReportSerializer


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
