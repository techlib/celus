from django.contrib import admin
from mptt.admin import MPTTModelAdmin

from . import models


@admin.register(models.Organization)
class OrganizationAdmin(MPTTModelAdmin):

    list_display = ['internal_id', 'short_name', 'name', 'ico']
    search_fields = ['internal_id', 'short_name', 'name', 'ico']


@admin.register(models.UserOrganization)
class OrganizationAdmin(admin.ModelAdmin):

    list_display = ['user', 'organization']
