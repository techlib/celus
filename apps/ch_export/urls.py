from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import AccessLogExportBatchProgressView, AccessLogExportViewSet

router = SimpleRouter()
router.register(r"exports", AccessLogExportViewSet, basename="ch-export-exports")

urlpatterns = router.urls + [
    path(
        "batches/<int:pk>/progress/",
        AccessLogExportBatchProgressView.as_view(),
        name="ch-export-batch-progress",
    )
]
