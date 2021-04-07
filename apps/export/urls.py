from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'flexible-export', views.FlexibleDataExportViewSet, basename='flexible-export')

urlpatterns = router.urls
