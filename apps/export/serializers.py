from api.auth import extract_org_from_request_api_key
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.fields import HiddenField
from rest_framework.serializers import ModelSerializer

from export.models import FlexibleDataAPIExport, FlexibleDataExport


class FlexibleDataExportSerializer(ModelSerializer):
    class Meta:
        model = FlexibleDataExport
        fields = (
            "pk",
            "name",
            "created",
            "last_updated",
            "status",
            "output_file",
            "export_params",
            "progress",
            "file_size",
            "file_format",
            "error_info",
        )


class CurrentOrgDefault:
    # inspired by CurrentUserDefault
    requires_context = True

    def __call__(self, serializer_field):
        return extract_org_from_request_api_key(serializer_field.context["request"])

    def __repr__(self):
        return "%s()" % self.__class__.__name__


class FlexibleDataAPIExportSerializer(ModelSerializer):
    owner_org = HiddenField(default=CurrentOrgDefault())

    class Meta:
        model = FlexibleDataAPIExport
        fields = (
            "pk",
            "report",
            "start_date",
            "end_date",
            "created",
            "last_updated",
            "status",
            "output_file",
            "progress",
            "file_size",
            "file_format",
            "error_info",
            "owner_org",
        )

    def validate(self, data):
        data = super().validate(data)
        report = data["report"]
        if report.owner_organization != data["owner_org"]:
            raise PermissionDenied("The report does not belong to the organization")
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        if start_date and not end_date:
            raise ValidationError("`end_date` is required when `start_date` is provided")
        if end_date and not start_date:
            raise ValidationError("`start_date` is required when `end_date` is provided")
        if start_date and end_date and (start_date > end_date):
            raise ValidationError("Start date must be before end date")
        return data

    def validate_file_format(self, value):
        return FlexibleDataAPIExport.cleanup_format(value)
