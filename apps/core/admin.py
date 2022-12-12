from allauth.account.adapter import get_adapter

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import TabularInline
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.db.models import Exists, OuterRef
from import_export.admin import ExportActionMixin
from import_export.resources import ModelResource

from organizations.models import UserOrganization
from .models import User, Identity, DataSource


class MyUserResource(ModelResource):
    """
    This is used by django-import-export to facilitate CSV export in Django admin
    """

    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'first_name',
            'last_name',
            'last_login',
            'is_active',
            'is_staff',
            'source',
        )
        export_order = fields


class UserOrganizationInline(TabularInline):
    model = UserOrganization
    fields = ['organization', 'is_admin']
    extra = 1


class IsAdminInAtLeastOneOrganization(admin.SimpleListFilter):
    title = _('is admin in at least one organization')

    parameter_name = 'is_admin'

    def lookups(self, request, model_admin):
        return (('Yes', _('Yes')), ('No', _('No')))

    def queryset(self, request, queryset):
        if self.value() == 'Yes':
            return queryset.filter(userorganization__is_admin=True).distinct()
        if self.value() == 'No':
            return queryset.exclude(userorganization__is_admin=True).distinct()


class IsAdminOfMasterOrganization(admin.SimpleListFilter):
    title = _('is consortial admin')

    parameter_name = 'is_consortial_admin'

    def lookups(self, request, model_admin):
        return (('Yes', _('Yes')), ('No', _('No')))

    def queryset(self, request, queryset):
        master_admin_filter = Exists(
            UserOrganization.objects.filter(
                is_admin=True,
                user=OuterRef('pk'),
                organization__internal_id__in=settings.MASTER_ORGANIZATIONS,
            )
        )
        if self.value() == 'Yes':
            return queryset.filter(master_admin_filter)

        if self.value() == 'No':
            return queryset.filter(~master_admin_filter)


@admin.register(User)
class MyUserAdmin(ExportActionMixin, UserAdmin):

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

    fieldsets = (
        UserAdmin.fieldsets[:2] + (("Celus", {'fields': custom_fields}),) + UserAdmin.fieldsets[2:]
    )
    add_fieldsets = UserAdmin.add_fieldsets + (("Celus", {'fields': custom_fields}),)

    list_filter = (
        'source',
        IsAdminInAtLeastOneOrganization,
        IsAdminOfMasterOrganization,
    ) + UserAdmin.list_filter

    actions = ['send_invitation_emails']
    inlines = [UserOrganizationInline]
    resource_class = MyUserResource  # for django-import-export

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        res = super().formfield_for_choice_field(db_field, request, **kwargs)
        if db_field.name == "language":
            # Limit language choice according to current settings
            res.choices = [e for e in res.choices if e in settings.LANGUAGES]
        return res

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
