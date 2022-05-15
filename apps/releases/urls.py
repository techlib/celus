from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'releases', views.Releases, basename='releases')
router.register(r'changelog', views.Changelog, basename='changelog')

urlpatterns = router.urls
