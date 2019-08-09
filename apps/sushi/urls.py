from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register(r'sushi-credentials', views.SushiCredentialsViewSet, basename='sushi-credentials')
router.register(r'counter-report-type', views.CounterReportTypeViewSet)

urlpatterns = [
]

urlpatterns += router.urls
