from api.models import OrganizationAPIKey
from django.contrib import admin
from rest_framework_api_key.admin import APIKeyModelAdmin


@admin.register(OrganizationAPIKey)
class OrganizationAPIKeyAdmin(APIKeyModelAdmin):

    list_display = [*APIKeyModelAdmin.list_display, 'organization']
    search_fields = [*APIKeyModelAdmin.search_fields, 'organization__name']
