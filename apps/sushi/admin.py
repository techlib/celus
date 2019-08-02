from django.contrib import admin

from . import models


@admin.register(models.SushiCredentials)
class SushiCredentialsAdmin(admin.ModelAdmin):

    list_display = ['organization', 'platform', 'version', 'client_id', 'requestor_id', 'enabled']
    list_filter = ['enabled', 'version', 'organization', 'platform']
