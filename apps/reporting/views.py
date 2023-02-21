from core.logic.dates import parse_month
from core.validators import month_validator
from django.http import HttpResponse
from organizations.models import Organization
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .logic.computation import Report
from .logic.export import XlsxExporter
from .logic.report_definitions import REPORTS, get_report_def_by_name


class ReportListView(APIView):
    def get(self, request):
        return Response(REPORTS)


class ReportDataView(APIView):
    class ParamSerializer(serializers.Serializer):
        start_date = serializers.CharField(validators=[month_validator], required=True)
        end_date = serializers.CharField(validators=[month_validator], required=True)
        organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all())

    def create_report(self, report_name) -> Report:
        report_def = get_report_def_by_name(report_name)
        if report_def is None:
            raise NotFound(f'Report with name "{report_name}" not found')
        return Report.from_definition(report_def)

    def get_params(self, request) -> dict:
        param_ser = self.ParamSerializer(data=request.query_params)
        param_ser.is_valid(raise_exception=True)
        if (
            not request.user.accessible_organizations()
            .filter(pk=param_ser.validated_data['organization'].pk)
            .exists()
        ):
            raise PermissionDenied(
                {"error": "User is not allowed to access the selected organization"}
            )
        data = dict(param_ser.validated_data)
        data['start_date'] = parse_month(data['start_date'])
        data['end_date'] = parse_month(data['end_date'])
        return data

    def get(self, request, report_name):
        report = self.create_report(report_name)
        params = self.get_params(request)
        report.retrieve_data(**params)
        out = []
        for i, (part, data) in enumerate(report.gen_output()):
            out.append(
                {"part_idx": i, "part_name": part.name, "data": [row.as_dict() for row in data]}
            )
        return Response(out)


class ReportExportView(ReportDataView):
    def get(self, request, report_name):
        report = self.create_report(report_name)
        params = self.get_params(request)
        report.retrieve_data(**params)
        exporter = XlsxExporter(report)
        export_data = exporter.export()
        return HttpResponse(
            export_data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f'attachment; filename="{report.name}.xlsx"'},
        )
