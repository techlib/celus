from django.conf import settings
from django.contrib import admin
from modeltranslation.admin import TranslationAdmin

from . import models


@admin.register(models.Organization)
class OrganizationAdmin(TranslationAdmin):

    list_display = ['short_name', 'internal_id', 'name', 'ico', 'source',] + (
        ['raw_data_import_enabled'] if settings.ENABLE_RAW_DATA_IMPORT == "PerOrg" else []
    )
    search_fields = ['internal_id', 'short_name', 'name', 'ico']
    list_filter = ['source'] + (
        ['raw_data_import_enabled'] if settings.ENABLE_RAW_DATA_IMPORT == "PerOrg" else []
    )
    list_select_related = ['source']


@admin.register(models.UserOrganization)
class UserOrganizationAdmin(admin.ModelAdmin):

    list_display = ['user', 'organization', 'is_admin', 'source']
    autocomplete_fields = ['user', 'organization']
    list_filter = ['source']
    list_select_related = ['source', 'organization', 'user']
    search_fields = [
        'user__username',
        'user__email',
        'organization__name',
        'organization__short_name',
    ]


@admin.register(models.OrganizationAltName)
class OrganizationAltNameAdmin(admin.ModelAdmin):

    list_display = ['organization', 'name']
    list_filter = ['organization']
    list_select_related = ['organization']
    search_fields = ['organization__name', 'organization__short_name', 'name']
