from rest_framework_nested.routers import NestedSimpleRouter

from organizations.urls import router as organization_router
from . import views

org_sub_router = NestedSimpleRouter(organization_router, r'organization', lookup='organization')
org_sub_router.register(r'platform', views.PlatformViewSet, basename='platform')
org_sub_router.register(r'detailed-platform', views.DetailedPlatformViewSet,
                        basename='detailed-platform')

urlpatterns = [
]

urlpatterns += org_sub_router.urls
