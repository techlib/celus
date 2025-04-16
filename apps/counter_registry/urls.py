from rest_framework.routers import SimpleRouter

from .views import PlatformDiffViewSet

router = SimpleRouter()
router.register("platforms_diff", PlatformDiffViewSet, basename="counter-platforms")

urlpatterns = router.urls
