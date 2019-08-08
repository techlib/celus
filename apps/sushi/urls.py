from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register(r'sushi-credentials', views.SushiCredentialsViewSet, basename='sushi-credentials')

urlpatterns = [
]

urlpatterns += router.urls
