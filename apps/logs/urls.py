from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'report-type', views.ReportTypeViewSet, basename='report-type')
router.register(r'metric', views.MetricViewSet)
router.register(r'report-interest-metric', views.ReportInterestMetricViewSet)
router.register(r'import-batch', views.ImportBatchViewSet, basename='import-batch')
router.register(r'manual-data-upload', views.ManualDataUploadViewSet, basename='manual-data-upload')
router.register(r'interest-groups', views.InterestGroupViewSet)
router.register(r'dimension-text', views.DimensionTextViewSet, basename='dimension-text')
router.register(r'flexible-report', views.FlexibleReportViewSet, basename='flexible-report')

urlpatterns = [
    path(
        'chart-data-raw/<report_type_id>/', views.Counter5DataView.as_view(), name='chart_data_raw'
    ),
    path('raw-data/', views.RawDataExportView.as_view()),
    path('raw-data-export/', views.RawDataDelayedExportView.as_view(), name='raw_data_export'),
    path(
        'raw-data-export/progress/<handle>',
        views.RawDataDelayedExportProgressView.as_view(),
        name='raw_data_export_progress',
    ),
    path('flexible-slicer/', views.FlexibleSlicerView.as_view(), name='flexible-slicer'),
    path(
        'flexible-slicer/possible-values/',
        views.FlexibleSlicerPossibleValuesView.as_view(),
        name='flexible-slicer-possible-values',
    ),
    path(
        'flexible-slicer/parts/',
        views.FlexibleSlicerSplitParts.as_view(),
        name='flexible-slicer-split-parts',
    ),
]

urlpatterns += router.urls
