import json

from django import forms
from django.conf import settings
from django.contrib import admin
from django.utils.html import format_html
from modeltranslation.admin import TranslationAdmin

from . import models


def create_default_interests(modeladmin, request, queryset):
    for platform in queryset:
        platform.create_default_interests()


def flush_knowledgebase(modeladmin, request, queryset):
    queryset.update(knowledgebase=None)


create_default_interests.short_description = "Create default interest for selected platforms"


@admin.register(models.Platform)
class PlatformAdmin(TranslationAdmin):

    list_display = ['short_name', 'name', 'provider', 'url', 'has_knowledgebase', 'source']
    list_select_related = ['source']
    list_filter = [('knowledgebase', admin.EmptyFieldListFilter), 'source']
    ordering = ['short_name']
    search_fields = ['short_name', 'provider'] + [
        f'name_{code}' for code, name in settings.LANGUAGES
    ]
    readonly_fields = ['pretty_knowledgebase']
    exclude = ['knowledgebase']
    actions = (create_default_interests, flush_knowledgebase)

    def has_knowledgebase(self, obj):
        return bool(obj.knowledgebase)

    has_knowledgebase.boolean = True
    has_knowledgebase.admin_order_field = 'knowledgebase'

    def pretty_knowledgebase(self, obj):
        return format_html(
            "<div style='max-height: 30em;overflow-y:scroll'><pre>{}</pre></div>",
            json.dumps(obj.knowledgebase, indent=2),
        )

    pretty_knowledgebase.allow_tags = True
    pretty_knowledgebase.short_description = "Knowledgebase"


@admin.register(models.PlatformInterestReport)
class PlatformInterestReportAdmin(admin.ModelAdmin):

    list_display = ['platform', 'report_type', 'last_modified']
    list_filter = ['report_type', 'platform']
    search_fields = ['platform__short_name', 'platform__name', 'platform__provider']


@admin.register(models.Title)
class TitleAdmin(admin.ModelAdmin):

    list_display = ['name', 'pub_type', 'isbn', 'issn', 'eissn', 'doi']
    search_fields = ['name', 'isbn', 'issn', 'eissn', 'doi']


@admin.register(models.PlatformTitle)
class PlatformTitleAdmin(admin.ModelAdmin):

    list_display = ['platform', 'organization', 'title', 'date']
    list_filter = ['platform', 'organization']
    readonly_fields = ['platform', 'organization', 'title', 'date']
    search_fields = ['platform__name', 'title__name']
