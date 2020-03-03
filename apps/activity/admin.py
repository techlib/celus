from django.contrib import admin

from .models import UserActivity


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):

    list_display = ['user', 'timestamp', 'action_type']
    list_filter = ['user']
    search_fields = ['user__email', 'user__username']
