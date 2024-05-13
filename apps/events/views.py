from collections import Counter

from core.logic.type_conversion import to_bool
from django.db.models import Exists, OuterRef
from django.utils.timezone import now
from logs.filters import OrderByFilter
from logs.views import StandardResultsSetPagination
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.response import Response

from events.event_filters import CategoryFilter, ImportanceFilter, ReadStatusFilter
from events.models import (
    Event,
    EventCategory,
    EventImportance,
    HandlingMethod,
    UserEvent,
    UserEventCategoryHandling,
)
from events.serializers import EventSerializer, UserEventFilterSerializer


class UserEventsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EventSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [
        ImportanceFilter,
        CategoryFilter,
        ReadStatusFilter,
        SearchFilter,
        OrderByFilter,
    ]
    search_fields = ["title", "description"]

    def get_queryset(self):
        return self.request.user.assigned_events.active().annotate(
            read=Exists(
                UserEvent.objects.filter(user=self.request.user, event=OuterRef("pk"), read=True)
            )
        )

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        """
        Mark the event as read for the user. Optionally, the `read` parameter can be passed
        to explicitly set the read status.

        This also sets the `first_read_date` if it's the first time the event changes its read
        status (even when it is from read to unread, even though this should not happen and
        obviously means some kind of mess).
        """
        read = to_bool(request.data.get("read", True))
        event = self.get_object()
        if ue := UserEvent.objects.filter(user=request.user, event=event).first():
            if ue.read != read:
                ue.read = read
                if not ue.first_read_date:
                    # first_read_date is only set the first time, not updated on subsequent reads
                    ue.first_read_date = now()
                ue.save()
                event.signal_stats_change(request.user)
        return self.retrieve(request, pk)

    @action(detail=False, methods=["post"], url_path="mark-read")
    def mark_read_many(self, request, pk=None):
        """
        Mark all event specified by a list of IDs as read for the user.

        Acts the same way as `mark_read` but for multiple events.
        """
        read = to_bool(request.data.get("read", True))
        event_ids = request.data.get("event_ids", [])
        stats = Counter({"updated": 0, "skipped": 0})
        for ue in UserEvent.objects.filter(user=request.user, event_id__in=event_ids):
            if ue.read != read:
                ue.read = read
                if not ue.first_read_date:
                    # first_read_date is only set the first time, not updated on subsequent reads
                    ue.first_read_date = now()
                ue.save()
                stats["updated"] += 1
            else:
                stats["skipped"] += 1
        if stats["updated"]:
            Event.signal_stats_change(request.user)
        return Response(stats)

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        filters_serializer = UserEventFilterSerializer(data=request.query_params)
        if filters_serializer.is_valid():
            filters = filters_serializer.validated_data
        else:
            filters = {}

        # Event query
        qs = request.user.assigned_events.active()
        qs = SearchFilter().filter_queryset(request, qs, self)

        filters["events"] = qs
        # UserEvent query
        out = request.user.userevent_set.stats(**filters)
        if out["newest_pk"]:
            out["newest_event"] = self.get_serializer(
                self.get_queryset().get(pk=out["newest_pk"])
            ).data
        else:
            out["newest_event"] = None
        return Response(out)


class UserEventPreferencesViewSet(viewsets.ViewSet):
    def list(self, request):
        """
        List all the user's event preferences.
        """
        category_importance_to_handling = {
            (ueh.category, ueh.importance): ueh.handling_method
            for ueh in self.request.user.usereventcategoryhandling_set.all()
        }
        out = {}
        for cat in EventCategory.values:
            out[cat] = {}
            for sev in EventImportance.values:
                out[cat][sev] = category_importance_to_handling.get(
                    (cat, sev), HandlingMethod.default()
                )
        return Response(out)

    def create(self, request):
        """
        Update preferences for the user.
        """
        category_importance_to_obj = {
            (ueh.category, ueh.importance): ueh
            for ueh in self.request.user.usereventcategoryhandling_set.all()
        }
        for cat, record in request.data.items():
            for imp, handling in record.items():
                imp = int(imp)  # it was sent as a string in the JSON (keys are always strings)
                if handling not in HandlingMethod.values:
                    return Response({"error": f"Invalid handling method: {handling}"}, status=400)
                if stored_obj := category_importance_to_obj.get((cat, imp)):
                    stored_obj.handling_method = handling
                    stored_obj.save()
                elif handling != HandlingMethod.default():
                    UserEventCategoryHandling.objects.create(
                        user=self.request.user,
                        category=cat,
                        importance=imp,
                        handling_method=handling,
                    )
        return self.list(request)
