from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"report-type", views.ReportTypeViewSet, basename="report-type")
router.register(r"metric", views.MetricViewSet)
router.register(
    r"report-interest-metric", views.ReportInterestMetricViewSet, basename="report-interest-metric"
)
router.register(r"import-batch", views.ImportBatchViewSet, basename="import-batch")
router.register(r"manual-data-upload", views.ManualDataUploadViewSet, basename="manual-data-upload")
router.register(r"interest-groups", views.InterestGroupViewSet)
router.register(r"dimension-text", views.DimensionTextViewSet, basename="dimension-text")
router.register(r"flexible-report", views.FlexibleReportViewSet, basename="flexible-report")
router.register(r"counter-data-export", views.CounterExportView, basename="counter-data-export")
router.register(r"report-mailing", views.FlexibleReportUserEmailViewSet, basename="report-mailing")
urlpatterns = [
    path(
        "chart-data-raw/<report_type_id>/", views.Counter5DataView.as_view(), name="chart_data_raw"
    ),
    path(
        "mdu-access-logs/<int:mdu_id>/",
        views.MduAccessLogListView.as_view(),
        name="mdu-access-logs",
    ),
    path(
        "ib-access-logs/<int:ib_id>/",
        views.ImportBatchAccessLogListView.as_view(),
        name="ib-access-logs",
    ),
    path(
        "mdu-heatmap-data/<int:mdu_id>/",
        views.MduHeatmapDataView.as_view(),
        name="mdu-heatmap-data",
    ),
    path("raw-data-export/", views.RawDataDelayedExportView.as_view(), name="raw_data_export"),
    path(
        "raw-data-export/progress/<handle>",
        views.RawDataDelayedExportProgressView.as_view(),
        name="raw_data_export_progress",
    ),
    path("flexible-slicer/", views.FlexibleSlicerView.as_view(), name="flexible-slicer"),
    path(
        "flexible-slicer/possible-values/",
        views.FlexibleSlicerPossibleValuesView.as_view(),
        name="flexible-slicer-possible-values",
    ),
    path(
        "flexible-slicer/parts/",
        views.FlexibleSlicerSplitParts.as_view(),
        name="flexible-slicer-split-parts",
    ),
    path(
        "flexible-slicer/remainder/",
        views.FlexibleSlicerRemainderView.as_view(),
        name="flexible-slicer-remainder",
    ),
    path(
        "flexible-slicer/coverage/",
        views.FlexibleSlicerCoverageView.as_view(),
        name="flexible-slicer-coverage",
    ),
]

urlpatterns += router.urls
