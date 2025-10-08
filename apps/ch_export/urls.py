from rest_framework.routers import SimpleRouter

from .views import AccessLogExportViewSet

router = SimpleRouter()
router.register(r"exports", AccessLogExportViewSet, basename="ch-export-exports")

urlpatterns = router.urls
