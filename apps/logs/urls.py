from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'report-type', views.ReportTypeViewSet)
router.register(r'metric', views.MetricViewSet)

urlpatterns = [
    path('chart-data/<report_name>/', views.Counter5DataView.as_view(), name='chart_data'),
]

urlpatterns += router.urls
