import json

from django.contrib import admin
from django.utils.html import format_html

from .models import ParserDefinition


@admin.register(ParserDefinition)
class ParserDefintionAdmin(admin.ModelAdmin):
    list_display = ('short_name', 'report_type_short_name', 'platforms', 'version')
    search_fields = ('short_name', 'report_type_short_name')
    readonly_fields = ('short_name', 'report_type_short_name', 'version', 'pretty_definition')
    exclude = ('definition',)

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="definition")
    def pretty_definition(self, obj):
        return format_html(
            "<div style='max-height: 30em;overflow-y:scroll'><pre>{}</pre></div>",
            json.dumps(obj.definition, indent=2),
        )

    def platforms(self, obj):
        return ", ".join(obj.definition.get("platforms"))

    pretty_definition.allow_tags = True
