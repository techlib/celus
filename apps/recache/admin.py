from statistics import mean

import django
from django.contrib import admin
from .models import CachedQuery


@admin.register(CachedQuery)
class CachedQueryAdmin(admin.ModelAdmin):

    list_display = [
        'pk',
        'origin',
        'model',
        'django_version',
        'current_django',
        'last_updated',
        'last_queried',
        'hit_count',
        'avg_query_duration_str',
        'queryset_pickle_size',
    ]

    actions = ['force_renew', 'renew']

    @classmethod
    def queryset_pickle_size(cls, obj: CachedQuery):
        return len(obj.queryset_pickle)

    def current_django(self, obj: CachedQuery):
        return obj.django_version == django.get_version()

    current_django.boolean = True

    def avg_query_duration_str(self, obj: CachedQuery):
        return obj.avg_query_duration or '-'

    avg_query_duration_str.short_description = 'Avg duration'

    def renew(self, request, queryset):
        for obj in queryset:
            obj.renew()

    renew.allowed_permissions = ('change',)

    def force_renew(self, request, queryset):
        for obj in queryset:
            obj.force_renew()

    force_renew.allowed_permissions = ('change',)