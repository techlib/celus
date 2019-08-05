from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, Identity, DataSource


@admin.register(User)
class MyUserAdmin(UserAdmin):

    list_display = UserAdmin.list_display + ('language',)

    custom_fields = ('ext_id', 'source', 'language')

    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': custom_fields}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': custom_fields}),
    )


@admin.register(Identity)
class IdentityAdmin(admin.ModelAdmin):

    list_display = ['identity', 'user', 'source']


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):

    list_display = ['short_name', 'type', 'url', 'organization']
