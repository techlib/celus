from django.contrib import admin
from modeltranslation.admin import TranslationAdmin

from . import models


@admin.register(models.Platform)
class PlatformAdmin(TranslationAdmin):

    list_display = ['short_name', 'name', 'provider', 'url']
    ordering = ['short_name']
    search_fields = ['short_name', 'name', 'provider']


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

    list_display = ['platform', 'organization', 'title']
    list_filter = ['platform', 'organization']
