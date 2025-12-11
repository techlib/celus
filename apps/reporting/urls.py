from django.urls import path

from . import views

urlpatterns = [
    path("reporting/reports/", views.ReportListView.as_view(), name="report-list"),
    path("reporting/reports/<str:report_id>/", views.ReportDataView.as_view(), name="report-data"),
    path(
        "reporting/reports/<str:report_id>/export/",
        views.ReportExportView.as_view(),
        name="report-export",
    ),
    path("reporting/anomaly-report/", views.AnomalyReportView.as_view(), name="anomaly-report"),
    path(
        "reporting/anomaly-report/details/",
        views.AnomalyDetailsView.as_view(),
        name="anomaly-details",
    ),
]
