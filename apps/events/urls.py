from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"user-events", views.UserEventsViewSet, basename="user-events")
router.register(
    "user-preferences", views.UserEventPreferencesViewSet, basename="user-event-preferences"
)

urlpatterns = [*router.urls]
