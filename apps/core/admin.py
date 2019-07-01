from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, Identity, DataSource


@admin.register(User)
class MyUserAdmin(UserAdmin):

    pass


@admin.register(Identity)
class IdentityAdmin(admin.ModelAdmin):

    list_display = ['identity', 'user', 'source']


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):

    list_display = ['short_name', 'type', 'url', 'organization']
