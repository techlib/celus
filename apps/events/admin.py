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
    list_filter = ("importance", "category", "platform")
    search_fields = (
        "title",
        "description",
        "expiration_date",
        "importance",
        "category",
        "platform__name",
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
    list_display = (
        "user",
        "event",
        "event_category",
        "event_importance",
        "read",
        "handling",
        "email_sent_date",
    )
    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
        "event__title",
        "event__description",
        "handling",
    )
    list_filter = ("handling", "read", "event__category", "event__importance", "user")

    def event_category(self, obj: models.UserEvent):
        return obj.event.get_category_display()

    def event_importance(self, obj: models.UserEvent):
        return obj.event.get_importance_display()
