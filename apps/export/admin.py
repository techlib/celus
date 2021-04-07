from django.contrib import admin, messages

from .models import FlexibleDataExport


@admin.register(FlexibleDataExport)
class FlexibleDataExportAdmin(admin.ModelAdmin):

    list_display = ['pk', 'owner', 'status', 'created', 'output_file']

    actions = ['create_output_file']

    def create_output_file(self, request, queryset):
        counter = 0
        for fe in queryset:  # type: FlexibleDataExport
            fe.create_output_file()
            counter += 1
        messages.add_message(request, messages.SUCCESS, f'{counter} exports processed')

    create_output_file.allowed_permissions = ('change',)
