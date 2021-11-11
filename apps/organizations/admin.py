from django.contrib import admin
from mptt.admin import MPTTModelAdmin

from modeltranslation.admin import TranslationAdmin

from . import models


@admin.register(models.Organization)
class OrganizationAdmin(MPTTModelAdmin, TranslationAdmin):

    list_display = ['short_name', 'internal_id', 'name', 'ico', 'source']
    search_fields = ['internal_id', 'short_name', 'name', 'ico']
    list_filter = ['source']
    list_select_related = ['source']


@admin.register(models.UserOrganization)
class UserOrganizationAdmin(admin.ModelAdmin):

    list_display = ['user', 'organization', 'is_admin', 'source']
    autocomplete_fields = ['user', 'organization']
    list_filter = ['source']
    list_select_related = ['source', 'organization', 'user']
    search_fields = ['user__username', 'user__email']


@admin.register(models.OrganizationAltName)
class OrganizationAltNameAdmin(admin.ModelAdmin):

    list_display = ['organization', 'name']
    list_filter = ['organization']
    list_select_related = ['organization']
    search_fields = ['organization__name', 'organization__short_name', 'name']
