from django.urls import path, include

from . import views

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
