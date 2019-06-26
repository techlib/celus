from django.urls import path

from . import views

urlpatterns = [
    path('chart-data/', views.Counter5DataView.as_view(), name='chart_data'),
]
