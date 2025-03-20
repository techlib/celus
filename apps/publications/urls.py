from django.urls import path
from logs.views import OrganizationManualDataUploadViewSet, OrganizationReportTypesViewSet
from organizations.urls import router as organization_router
from rest_framework.routers import SimpleRouter
from rest_framework_nested.routers import NestedSimpleRouter

from . import views

root_router = SimpleRouter()

org_sub_router = NestedSimpleRouter(organization_router, r"organization", lookup="organization")
org_sub_router.register(r"platform", views.PlatformViewSet, basename="platform")
org_sub_router.register(r"all-platform", views.AllPlatformsViewSet, basename="all-platforms")
org_sub_router.register(
    r"platform-interest", views.PlatformInterestViewSet, basename="platform-interest"
)
org_sub_router.register("title", views.TitleViewSet, basename="title")
org_sub_router.register(r"title-interest", views.TitleInterestViewSet, basename="title-interest")
org_sub_router.register(
    r"title-interest-brief", views.TitleInterestBriefViewSet, basename="title-interest-brief"
)
org_sub_router.register(
    r"top-title-interest", views.TopTitleInterestViewSet, basename="top-title-interest"
)

org_sub_router.register("item", views.ItemViewSet, basename="organization-item")

org_sub_router.register(
    r"report-types", OrganizationReportTypesViewSet, basename="organization-report-types"
)
org_sub_router.register(
    r"manual-data-upload",
    OrganizationManualDataUploadViewSet,
    basename="organization-manual-data-upload",
)
org_sub_router.register(r"alt-names", views.OrganizationAltNameViewSet, basename="alt-name")


title_sub_router = NestedSimpleRouter(org_sub_router, r"title", lookup="title")
title_sub_router.register(
    "report-views", views.TitleReportDataViewViewSet, basename="title-report-data-views"
)
title_sub_router.register("item", views.ItemViewSet, basename="organization-title-items")

title_item_sub_router = NestedSimpleRouter(title_sub_router, r"item", lookup="item")
title_item_sub_router.register(
    "report-views", views.ItemReportDataViewViewSet, basename="title-item-report-data-views"
)


platform_sub_router = NestedSimpleRouter(org_sub_router, r"platform", lookup="platform")
platform_sub_router.register("title", views.PlatformTitleViewSet, basename="platform-title")
platform_sub_router.register(
    "title-interest", views.PlatformTitleInterestViewSet, basename="platform-title-interest"
)
platform_sub_router.register(
    "report-views", views.PlatformReportDataViewViewSet, basename="platform-report-data-views"
)

platform_title_sub_router = NestedSimpleRouter(platform_sub_router, r"title", lookup="title")
platform_title_sub_router.register(
    "report-views",
    views.PlatformTitleReportDataViewViewSet,
    basename="platform-title-report-data-views",
)
platform_title_sub_router.register(
    "item", views.ItemViewSet, basename="organization-platform-title-items"
)

platform_title_item_sub_router = NestedSimpleRouter(
    platform_title_sub_router, r"item", lookup="item"
)
platform_title_item_sub_router.register(
    "report-views",
    views.ItemReportDataViewViewSet,
    basename="platform-title-item-report-data-views",
)

platform_sub_router.register("item", views.ItemViewSet, basename="organization-platform-items")

root_router.register(r"platform", views.GlobalPlatformsViewSet, basename="global-platforms")
root_router.register(r"title", views.GlobalTitleViewSet, basename="global-titles")

root_router.register(
    "title-overlap-batch", views.TitleOverlapBatchViewSet, basename="title-overlap-batch"
)

root_router.register("item", views.ItemViewSet, basename="global-items")

urlpatterns = [path("run-task/erms-sync-platforms", views.StartERMSSyncPlatformsTask.as_view())]

urlpatterns += root_router.urls
urlpatterns += org_sub_router.urls
urlpatterns += platform_sub_router.urls
urlpatterns += title_sub_router.urls
urlpatterns += platform_title_sub_router.urls
urlpatterns += platform_title_item_sub_router.urls
urlpatterns += title_item_sub_router.urls
