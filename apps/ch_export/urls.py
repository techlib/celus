from django.urls import path

from .views import AccessLogExportList

urlpatterns = [path("logs/", AccessLogExportList.as_view(), name="ch-export-logs")]
