from django.urls import path

from . import views

urlpatterns = [
    path('reporting/reports/', views.ReportListView.as_view(), name='report-list'),
    path(
        'reporting/reports/<str:report_name>/', views.ReportDataView.as_view(), name='report-data'
    ),
    path(
        'reporting/reports/<str:report_name>/export/',
        views.ReportExportView.as_view(),
        name='report-export',
    ),
]
