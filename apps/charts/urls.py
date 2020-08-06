from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(
    r'report-view-to-chart', views.ReportViewToChartTypeViewSet, basename='report-view-to-chart'
)
router.register(r'report-view', views.ReportDataViewViewSet, basename='report-view')
router.register(r'chart-definition', views.ChartDefinitionViewSet, basename='chart-definition')

urlpatterns = [
    path(
        'report-data-view/<view_pk>/chart-definitions/',
        views.ReportDataViewChartDefinitions.as_view(),
        name='report-data-view-chart-definitions',
    ),
    path(
        'report-type/<report_type_pk>/report-views/',
        views.ReportTypeToReportDataViewView.as_view(),
        name='report-type-to-report-data-view',
    ),
    path('chart-data/<report_view_id>/', views.ChartDataView.as_view(), name='chart_data'),
]

urlpatterns += router.urls
