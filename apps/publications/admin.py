from django.contrib import admin

from . import models


@admin.register(models.Platform)
class PlatformAdmin(admin.ModelAdmin):

    list_display = ['short_name', 'name', 'provider', 'url']


@admin.register(models.Title)
class TitleAdmin(admin.ModelAdmin):

    list_display = ['name', 'pub_type', 'isbn', 'issn', 'eissn', 'doi']
