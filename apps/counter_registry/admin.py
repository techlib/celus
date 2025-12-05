import json

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django_celus_registry import models as orig_models

from .models import (
    CounterRegistryProfile,
    NotificationEvent,
    Platform,
    PlatformExtras,
    SushiService,
)

admin.site.unregister(orig_models.Platform)
admin.site.unregister(orig_models.SushiService)
admin.site.unregister(orig_models.Notification)


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


@admin.register(NotificationEvent)
class NotificationEventAdmin(admin.ModelAdmin):
    list_display = ("subject", "start_date", "end_date", "platform")
    select_related = ("notification", "event")

    @admin.display(description="subject", ordering="notification__subject")
    def subject(self, obj):
        return obj.notification.subject

    @admin.display(description="start_date", ordering="notification__start_date")
    def start_date(self, obj):
        return obj.notification.start_date

    @admin.display(description="end_date", ordering="notification__end_date")
    def end_date(self, obj):
        return obj.notification.end_date

    @admin.display(description="platform", ordering="event__platform__name")
    def platform(self, obj):
        if obj.event.platform:
            return obj.event.platform.name
        return ""

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return False


@admin.register(CounterRegistryProfile)
class CounterRegistryProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "events_from_counter_registry", "last_registry_event_date")
    readonly_fields = ("user",)
    select_related = ("user",)

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, request, obj=None):
        if request.resolver_match.view_name == "admin:core_user_changelist":
            # allow deleting counter registry profiles in cascade when deleting users
            return super().has_delete_permission(request, obj)
        return False


@admin.register(orig_models.Notification)
class NotificationAdmin(admin.ModelAdmin):
    def has_add_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return False
