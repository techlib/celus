from allauth.account.adapter import get_adapter

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin

from .models import User, Identity, DataSource


@admin.register(User)
class MyUserAdmin(UserAdmin):

    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'last_login',
        'is_active',
        'is_staff',
        'source',
    )

    custom_fields = ('ext_id', 'source', 'language', 'extra_data')

    fieldsets = UserAdmin.fieldsets + ((None, {'fields': custom_fields}),)
    add_fieldsets = UserAdmin.add_fieldsets + ((None, {'fields': custom_fields}),)

    list_filter = ('source',) + UserAdmin.list_filter

    actions = ['send_invitation_emails']

    def send_invitation_emails(self, request, queryset):
        adapter = get_adapter()
        sent_messages = 0
        for user in queryset.all():
            try:
                adapter.send_invitation_email(request, user)
            except ValueError as exc:
                messages.add_message(request, messages.ERROR, f'Error sending invitations: {exc}')
                return
            sent_messages += 1
        messages.add_message(request, messages.SUCCESS, f'Sent {sent_messages} invitation(s)')

    send_invitation_emails.allowed_permissions = ('change',)


@admin.register(Identity)
class IdentityAdmin(admin.ModelAdmin):

    list_display = ['identity', 'user', 'source']
    list_filter = ['source']
    list_select_related = ['user', 'source']
    search_fields = ['identity', 'user__email', 'user__username']


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):

    list_display = ['short_name', 'type', 'url', 'organization']
