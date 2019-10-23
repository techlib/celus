from django.contrib import admin
from modeltranslation.admin import TranslationAdmin

from . import models


@admin.register(models.Platform)
class PlatformAdmin(TranslationAdmin):

    list_display = ['short_name', 'name', 'provider', 'url']
    ordering = ['short_name']


@admin.register(models.PlatformInterestReport)
class PlatformInterestReportAdmin(admin.ModelAdmin):

    list_display = ['platform', 'report_type', 'last_modified']
    list_filter = ['report_type']


@admin.register(models.Title)
class TitleAdmin(admin.ModelAdmin):

    list_display = ['name', 'pub_type', 'isbn', 'issn', 'eissn', 'doi']
    search_fields = ['name', 'isbn', 'issn', 'eissn', 'doi']
