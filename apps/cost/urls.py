from organizations.urls import router as organization_router
from rest_framework_nested.routers import NestedSimpleRouter

from . import views

org_sub_router = NestedSimpleRouter(organization_router, r'organization', lookup='organization')
org_sub_router.register(r'payments', views.OrganizationPaymentViewSet, basename='payments')

urlpatterns = [] + org_sub_router.urls
