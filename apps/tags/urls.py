from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedSimpleRouter

from . import views

router = DefaultRouter()
router.register(r'tag-class', views.TagClassViewSet, basename='tag-class')
router.register(r'tag', views.TagViewSet, basename='tag')

tagged_titles_router = NestedSimpleRouter(router, r'tag', lookup='tag')
tagged_titles_router.register(r'title', views.TaggedTitleViewSet, basename='tagged-titles')
tagged_titles_router.register(
    r'platform', views.TaggedPlatformsViewSet, basename='tagged-platforms'
)
tagged_titles_router.register(
    r'organization', views.TaggedOrganizationsViewSet, basename='tagged-organizations'
)

router.register(r'tagging-batch', views.TaggingBatchViewSet, basename='tagging-batch')

urlpatterns = [
    *router.urls,
    *tagged_titles_router.urls,
    path('tag-item-links/', views.TagItemLinksView.as_view(), name='tag-item-links'),
]
