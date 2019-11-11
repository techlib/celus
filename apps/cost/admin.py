from django.contrib import admin

from . import models


@admin.register(models.Payment)
class PaymentAdmin(admin.ModelAdmin):

    list_display = ['organization', 'platform', 'year', 'price']
    search_fields = ['organization__name', 'platform__name', 'platform__short_name']
    list_filter = ['year',
                   ('organization', admin.RelatedOnlyFieldListFilter),
                   ('platform', admin.RelatedOnlyFieldListFilter),
                   ]
    readonly_fields = ['last_updated_by']

    def save_model(self, request, obj, form, change):
        obj.last_updated_by = request.user
        super().save_model(request, obj, form, change)
