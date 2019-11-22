from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'report-type', views.ReportTypeViewSet, basename='report-type')
router.register(r'metric', views.MetricViewSet)
router.register(r'import-batch', views.ImportBatchViewSet)
router.register(r'manual-data-upload', views.ManualDataUploadViewSet,
                basename='manual-data-upload')
router.register(r'interest-groups', views.InterestGroupViewSet)

urlpatterns = [
    path('chart-data-raw/<report_type_id>/', views.Counter5DataView.as_view(),
         name='chart_data_raw'),
    path('chart-data-raw/', views.Counter5DataView.as_view(), {'report_type_id': None},
         name='chart_data_raw'),
    path('raw-data/', views.RawDataExportView.as_view()),
]

urlpatterns += router.urls
