from rest_framework.routers import SimpleRouter
from rest_framework_nested.routers import NestedSimpleRouter

from .views import HarvestIntentionViewSet, HarvestViewSet, IntentionViewSet

router = SimpleRouter()
router.register('harvest', HarvestViewSet, basename='harvest')
router.register('intention', IntentionViewSet, basename='intention')

harvest_router = NestedSimpleRouter(router, 'harvest', lookup='harvest')
harvest_router.register('intention', HarvestIntentionViewSet, basename='harvest-intention')

urlpatterns = [*router.urls, *harvest_router.urls]
