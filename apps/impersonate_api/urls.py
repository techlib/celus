from rest_framework.routers import SimpleRouter

from .views import ImpersonateViewSet

router = SimpleRouter()
router.register('impersonate', ImpersonateViewSet, basename='impersonate')

urlpatterns = router.urls
