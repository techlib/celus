from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'organization', views.OrganizationViewSet, basename='organization')

urlpatterns = [
]

urlpatterns += router.urls
