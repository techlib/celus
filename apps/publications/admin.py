import json

from django.conf import settings
from django.contrib import admin
from django.utils.html import format_html
from modeltranslation.admin import TranslationAdmin
from necronomicon.admin import NecronomiconAdminMixin

from . import models


def flush_knowledgebase(modeladmin, request, queryset):
    queryset.update(knowledgebase=None)


@admin.register(models.Platform)
class PlatformAdmin(NecronomiconAdminMixin, TranslationAdmin):
    list_display = [
        "short_name",
        "name",
        "provider",
        "url",
        "has_knowledgebase",
        "source",
        "ext_id",
        "duplicates",
    ]
    list_select_related = ["source"]
    list_filter = [("knowledgebase", admin.EmptyFieldListFilter), "source"]
    ordering = ["short_name"]
    search_fields = ["short_name", "provider"] + [
        f"name_{code}" for code, name in settings.LANGUAGES
    ]
    readonly_fields = ["pretty_knowledgebase"]
    exclude = ["knowledgebase"]
    actions = [flush_knowledgebase]

    def has_knowledgebase(self, obj):
        return bool(obj.knowledgebase)

    has_knowledgebase.boolean = True
    has_knowledgebase.admin_order_field = "knowledgebase"

    def pretty_knowledgebase(self, obj):
        return format_html(
            "<div style='max-height: 30em;overflow-y:scroll'><pre>{}</pre></div>",
            json.dumps(obj.knowledgebase, indent=2),
        )

    pretty_knowledgebase.allow_tags = True
    pretty_knowledgebase.short_description = "Knowledgebase"


@admin.register(models.Title)
class TitleAdmin(admin.ModelAdmin):
    list_display = ["name", "pub_type", "isbn", "issn", "eissn", "doi"]
    search_fields = ["name", "isbn", "issn", "eissn", "doi"]


@admin.register(models.Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ["name", "isni", "orcid"]
    search_fields = ["name", "isni", "orcid", "eissn", "doi"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


class AuthorInline(admin.TabularInline):
    model = models.Item.authors.through
    fields = ["position", "item", "author"]
    readonly_fields = ["position", "item", "author"]
    can_delete = False
    extra = 0

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(models.Item)
class ItemAdmin(admin.ModelAdmin):
    inlines = [AuthorInline]

    list_display = ["name", "publication_date", "isbn", "issn", "eissn", "doi"]
    search_fields = ["name", "isbn", "issn", "eissn", "doi"]


@admin.register(models.PlatformTitle)
class PlatformTitleAdmin(admin.ModelAdmin):
    list_display = ["platform", "organization", "title", "date"]
    list_filter = ["platform", "organization"]
    readonly_fields = ["platform", "organization", "title", "date"]
    search_fields = ["platform__name", "title__name"]


@admin.register(models.TitleOverlapBatch)
class TitleOverlapBatchAdmin(admin.ModelAdmin):
    list_display = ["last_updated", "last_updated_by", "state", "organization"]
