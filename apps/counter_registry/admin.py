import json

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django_celus_registry import models as orig_models

from .models import Platform, PlatformExtras, SushiService

admin.site.unregister(orig_models.Platform)
admin.site.unregister(orig_models.SushiService)


class ReportsInline(admin.TabularInline):
    model = Platform.reports.through

    def has_change_permission(self, *args, **kwargs):
        return False

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False


class SushiServiceInline(admin.TabularInline):
    show_change_link = True
    model = SushiService
    exclude = [
        "ip_address_authorization",
        "api_key_required",
        "platform_attr_required",
        "requestor_id_required",
    ]

    def has_change_permission(self, *args, **kwargs):
        return False

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    search_fields = ("name", "abbrev", "id")
    inlines = (SushiServiceInline, ReportsInline)
    list_display = ("name", "abbrev", "linked")
    readonly_fields = ("id", "abbrev", "name")

    @admin.display(ordering="linked")
    def linked(self, platform):
        if platform.linked:
            url = reverse("admin:publications_platform_change", args=[platform.related_platform])
            return format_html(f'<a href="{url}">Platform</a>')
        else:
            return "-"

    def registry(self, obj: Platform):
        return format_html(f'<a href="{obj.registry_url}">Registry</a>')

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return False


@admin.register(PlatformExtras)
class PlatformExtrasAdmin(admin.ModelAdmin):
    search_fields = ("platform__name", "platform__abbrev", "platform__id")
    list_display = (
        "platform_name",
        "platform_abbrev",
        "platform_content_provider_name",
        "platform_website",
    )
    readonly_fields = ("pretty_knowledgebase", "platform")
    exclude = ("knowledgebase",)

    @admin.display(description="name", ordering="platform__name")
    def platform_name(self, obj):
        return obj.platform.name

    @admin.display(description="Abbrev", ordering="platform__abbrev")
    def platform_abbrev(self, obj):
        return obj.platform.abbrev

    @admin.display(description="Content Provider Name", ordering="platform__content_provider_name")
    def platform_content_provider_name(self, obj):
        return obj.platform.content_provider_name

    @admin.display(description="Website", ordering="platform__website")
    def platform_website(self, obj):
        return obj.platform.website

    def has_add_permission(self, *args, **kwargs):
        return False

    def pretty_knowledgebase(self, obj):
        return format_html(
            "<div style='max-height: 30em;overflow-y:scroll'><pre>{}</pre></div>",
            json.dumps(obj.knowledgebase, indent=2),
        )

    pretty_knowledgebase.allow_tags = True
    pretty_knowledgebase.short_description = "Knowledgebase"
