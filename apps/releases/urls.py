from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'releases', views.Releases, basename='releases')

urlpatterns = [path('changelog/', views.ChangelogAPIView.as_view(), name='changelog')] + router.urls
