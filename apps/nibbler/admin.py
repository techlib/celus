from django.contrib import admin

from .models import ParserDefinition


@admin.register(ParserDefinition)
class ParserDefintionAdmin(admin.ModelAdmin):
    list_display = ('short_name', 'report_type_short_name', 'version')
    search_fields = ('short_name', 'report_type_short_name')
    readonly_fields = ('short_name', 'report_type_short_name', 'version', 'definition')

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False
