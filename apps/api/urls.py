import logging

from django.conf import settings
from django.urls import path, include

from rest_framework.renderers import JSONOpenAPIRenderer
from rest_framework.schemas import get_schema_view
from rest_framework.schemas.openapi import SchemaGenerator

from . import views

logger = logging.getLogger(__name__)

urlpatterns = [
    path('', include('logs.urls')),
    path('', include('organizations.urls')),
    path('', include('publications.urls')),
    path('', include('core.urls')),
    path('', include('sushi.urls')),
    path('', include('charts.urls')),
    path('', include('annotations.urls')),
    path('', include('cost.urls')),
]

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
