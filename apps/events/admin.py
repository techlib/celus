from django.contrib import admin
from django.db.models import Count

from . import models


class UserEventInline(admin.TabularInline):
    model = models.UserEvent
    fields = ["user", "handling"]


@admin.register(models.Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "description",
        "expiration_date",
        "importance",
        "category",
        "platform",
        "user_count",
    )
    search_fields = (
        "title",
        "description",
        "expiration_date",
        "importance",
        "category",
        "platform",
    )
    readonly_fields = ("created", "last_updated")

    inlines = [UserEventInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(user_count=Count("userevent"))

    def user_count(self, obj):
        return obj.user_count


@admin.register(models.UserEventCategoryHandling)
class UserEventCategoryHandlingAdmin(admin.ModelAdmin):
    list_display = ("user", "category", "importance", "handling_method")
    search_fields = ("user", "category", "handling_method")
    list_filter = ("category", "importance", "handling_method")


@admin.register(models.UserEvent)
class UserEventAdmin(admin.ModelAdmin):
    list_display = ("user", "event", "read", "handling", "email_sent_date")
    search_fields = ("user", "event", "handling")
    list_filter = ("handling", "read")
