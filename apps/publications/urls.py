from rest_framework_nested.routers import NestedSimpleRouter

from logs.views import CustomDimensionsViewSet, OrganizationReportTypesViewSet
from organizations.urls import router as organization_router
from . import views

org_sub_router = NestedSimpleRouter(organization_router, r'organization', lookup='organization')
org_sub_router.register(r'platform', views.PlatformViewSet, basename='platform')
org_sub_router.register(r'detailed-platform', views.DetailedPlatformViewSet,
                        basename='detailed-platform')
org_sub_router.register('title', views.TitleViewSet, basename='title')
org_sub_router.register(r'title-count', views.TitleCountsViewSet, basename='title-count')

org_sub_router.register(r'custom-dimensions', CustomDimensionsViewSet,
                        basename='custom-dimensions')
org_sub_router.register(r'report-types', OrganizationReportTypesViewSet,
                        basename='organization-report-types')


title_sub_router = NestedSimpleRouter(org_sub_router, r'title', lookup='title')
title_sub_router.register('reports', views.TitleReportTypeViewSet,
                          basename='title-reports')


platform_sub_router = NestedSimpleRouter(org_sub_router, r'platform', lookup='platform')
platform_sub_router.register('title', views.PlatformTitleViewSet, basename='platform-title')
platform_sub_router.register('title-count', views.PlatformTitleCountsViewSet,
                             basename='platform-title-count')
platform_sub_router.register('reports', views.PlatformReportTypeViewSet,
                             basename='platform-reports')

platform_title_sub_router = NestedSimpleRouter(platform_sub_router, r'title', lookup='title')
platform_title_sub_router.register('reports', views.PlatformTitleReportTypeViewSet,
                                   basename='platform-title-reports')

urlpatterns = [
]

urlpatterns += org_sub_router.urls
urlpatterns += platform_sub_router.urls
urlpatterns += title_sub_router.urls
urlpatterns += platform_title_sub_router.urls

