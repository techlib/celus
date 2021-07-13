import logging

from django.conf import settings
from django.urls import path, include

from rest_framework.renderers import JSONOpenAPIRenderer
from rest_framework.schemas import get_schema_view
from rest_framework.schemas.openapi import SchemaGenerator

from . import views

logger = logging.getLogger(__name__)

local_urls = [
    path(
        'platform/<int:platform_id>/report/<str:report_type>',
        views.PlatformReportView.as_view(),
        name='api_platform_report_data',
    ),
]

urlpatterns = [
    path('accounts/', include('django.contrib.auth.urls')),  # contains link to reset password
    path('rest-auth/', include('dj_rest_auth.urls')),
    path('', include('logs.urls')),
    path('', include('organizations.urls')),
    path('', include('publications.urls')),
    path('', include('core.urls')),
    path('', include('sushi.urls')),
    path('', include('charts.urls')),
    path('', include('annotations.urls')),
    path('', include('cost.urls')),
    *local_urls,
    path('export/', include('export.urls')),
    path('scheduler/', include('scheduler.urls')),
    path('deployment/', include('deployment.urls')),
]

if settings.ALLOW_USER_REGISTRATION:
    urlpatterns.append(path('rest-auth/registration/', include('dj_rest_auth.registration.urls')))


if settings.DEBUG:

    class CustomSchemaGenerator(SchemaGenerator):
        def has_view_permissions(self, path, method, view):  # generate schemas for all
            # only views with a a serializer can be used to generate schema
            # otherwise an exception is thrown
            try:
                view.get_serializer_class()
            except (AssertionError, AttributeError):
                logger.warning("Missing serializer for %s", type(view))
                return False
            return True

    schema_view = get_schema_view(
        title="OpenAPI schema",
        renderer_classes=[JSONOpenAPIRenderer],
        permission_classes=[],
        authentication_classes=[],
        generator_class=CustomSchemaGenerator,
    )
    urlpatterns = [
        path('openapi.json', schema_view, name='openapi-schema'),
        path('redoc', views.RedocView.as_view()),
    ] + urlpatterns
