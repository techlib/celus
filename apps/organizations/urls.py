from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'organization', views.OrganizationViewSet, basename='organization')

urlpatterns = [
    path('run-task/erms-sync-organizations', views.StartERMSSyncOrganizationsTask.as_view())
]

urlpatterns += router.urls
