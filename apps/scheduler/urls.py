from django.urls import path
from rest_framework.routers import SimpleRouter
from rest_framework_nested.routers import NestedSimpleRouter

from .views import HarvestViewSet, HarvestIntentionViewSet, IntentionViewSet, IntentionDeleteView

router = SimpleRouter()
router.register('harvest', HarvestViewSet, basename='harvest')
router.register('intention', IntentionViewSet, basename='intention')

harvest_router = NestedSimpleRouter(router, 'harvest', lookup='harvest')
harvest_router.register('intention', HarvestIntentionViewSet, basename='harvest-intention')

urlpatterns = [
    path('fetch-intention-delete/', IntentionDeleteView.as_view(), name='fetch-intention-delete'),
    *router.urls,
    *harvest_router.urls,
]
