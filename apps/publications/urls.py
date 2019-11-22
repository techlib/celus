from django.urls import path
from rest_framework.routers import SimpleRouter
from rest_framework_nested.routers import NestedSimpleRouter

from logs.views import CustomDimensionsViewSet, OrganizationReportTypesViewSet, \
    OrganizationManualDataUploadViewSet
from organizations.urls import router as organization_router
from . import views

root_router = SimpleRouter()
root_router.register(r'platform', views.AllPlatformsViewSet, basename='all-platforms')

org_sub_router = NestedSimpleRouter(organization_router, r'organization', lookup='organization')
org_sub_router.register(r'platform', views.PlatformViewSet, basename='platform')
org_sub_router.register(r'detailed-platform', views.DetailedPlatformViewSet,
                        basename='detailed-platform')
org_sub_router.register(r'platform-interest', views.PlatformInterestViewSet,
                        basename='platform-interest')
org_sub_router.register('title', views.TitleViewSet, basename='title')
org_sub_router.register(r'title-interest', views.TitleInterestViewSet, basename='title-interest')

org_sub_router.register(r'dimensions', CustomDimensionsViewSet,
                        basename='organization-dimensions')
org_sub_router.register(r'report-types', OrganizationReportTypesViewSet,
                        basename='organization-report-types')
org_sub_router.register(r'manual-data-upload', OrganizationManualDataUploadViewSet,
                        basename='organization-manual-data-upload')


title_sub_router = NestedSimpleRouter(org_sub_router, r'title', lookup='title')
title_sub_router.register('report-views', views.TitleReportDataViewViewSet,
                          basename='title-report-data-views')

platform_sub_router = NestedSimpleRouter(org_sub_router, r'platform', lookup='platform')
platform_sub_router.register('title', views.PlatformTitleViewSet, basename='platform-title')
platform_sub_router.register('title-interest', views.PlatformTitleInterestViewSet,
                             basename='platform-title-interest')
platform_sub_router.register('report-views', views.PlatformReportDataViewViewSet,
                             basename='platform-report-data-views')

platform_title_sub_router = NestedSimpleRouter(platform_sub_router, r'title', lookup='title')
platform_title_sub_router.register('report-views', views.PlatformTitleReportDataViewViewSet,
                                   basename='platform-title-report-data-views')

urlpatterns = [
    path('run-task/erms-sync-platforms', views.StartERMSSyncPlatformsTask.as_view())
]

urlpatterns += root_router.urls
urlpatterns += org_sub_router.urls
urlpatterns += platform_sub_router.urls
urlpatterns += title_sub_router.urls
urlpatterns += platform_title_sub_router.urls

