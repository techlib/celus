from django.urls import path

from . import views

urlpatterns = [
    path('report-data-view/<view_pk>/chart-definitions/',
         views.ReportDataViewChartDefinitions.as_view(),
         name='report-data-view-chart-definitions'),
    path('chart-data/<report_view_id>/', views.ChartDataView.as_view(), name='chart_data'),
]

