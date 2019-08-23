from django.contrib import admin
from mptt.admin import MPTTModelAdmin

from . import models


@admin.register(models.Organization)
class OrganizationAdmin(MPTTModelAdmin):

    list_display = ['internal_id', 'short_name', 'name', 'ico', 'source']
    search_fields = ['internal_id', 'short_name', 'name', 'ico']
    list_filter = ['source']
    list_select_related = ['source']


@admin.register(models.UserOrganization)
class UserOrganizationAdmin(admin.ModelAdmin):

    list_display = ['user', 'organization', 'is_admin', 'source']
    list_filter = ['source']
    list_select_related = ['source', 'organization', 'user']
    search_fields = ['user__username', 'user__email']
