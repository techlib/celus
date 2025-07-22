from django.conf import settings
from django.contrib import admin
from import_export.admin import ImportExportMixin
from import_export.formats.base_formats import CSV, XLSX
from import_export.resources import ModelResource
from modeltranslation.admin import TranslationAdmin
from necronomicon.admin import NecronomiconAdminMixin

from . import forms, models


class OrganizationResource(ModelResource):
    class Meta:
        model = models.Organization
        fields = ("id", "name", "short_name", "ror", "isni", "country", "state")


@admin.register(models.Organization)
class OrganizationAdmin(NecronomiconAdminMixin, ImportExportMixin, TranslationAdmin):
    import_formats = [CSV, XLSX]
    export_formats = [CSV, XLSX]
    form = forms.OrganizationForm
    list_display = ["short_name", "internal_id", "name", "ico", "source", "country", "state"] + (
        ["raw_data_import_enabled"] if settings.ENABLE_RAW_DATA_IMPORT == "PerOrg" else []
    )
    search_fields = ["internal_id", "short_name", "name", "ico"]
    list_filter = ["source"] + (
        ["raw_data_import_enabled"] if settings.ENABLE_RAW_DATA_IMPORT == "PerOrg" else []
    )
    list_select_related = ["source"]
    ordering = ["name"]
    readonly_fields = ("created", "last_modified")
    resource_class = OrganizationResource
    list_editable = ["country", "state"]


@admin.register(models.UserOrganization)
class UserOrganizationAdmin(admin.ModelAdmin):
    list_display = ["user", "organization", "is_admin", "source"]
    autocomplete_fields = ["user", "organization"]
    list_filter = ["source"]
    list_select_related = ["source", "organization", "user"]
    search_fields = [
        "user__username",
        "user__email",
        "organization__name",
        "organization__short_name",
    ]


@admin.register(models.OrganizationAltName)
class OrganizationAltNameAdmin(admin.ModelAdmin):
    list_display = ["organization", "name"]
    list_filter = ["organization"]
    list_select_related = ["organization"]
    search_fields = ["organization__name", "organization__short_name", "name"]
