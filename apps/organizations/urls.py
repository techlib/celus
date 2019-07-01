from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'organization-type', views.OrganizationViewSet, base_name='organization')

urlpatterns = [
]

urlpatterns += router.urls
