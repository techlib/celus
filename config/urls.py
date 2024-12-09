"""
CELUS URL Configuration
"""

from core.views import PrometheusMetricsView
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("api/", include("api.urls")),
    path("metrics", PrometheusMetricsView.as_view(), name="metrics"),
    path(settings.CELUS_ADMIN_SITE_PATH, admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__", include(debug_toolbar.urls))] + urlpatterns
