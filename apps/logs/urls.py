from django.urls import path

from . import views

urlpatterns = [
    path('chart-data/<report_name>/', views.Counter5DataView.as_view(), name='chart_data'),
]
