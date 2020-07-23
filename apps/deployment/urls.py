from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'footer-image', views.FooterImageViewSet, basename='footer-image')
router.register(r'site-logo', views.SiteLogoViewSet, basename='site-logo')
router.register(r'site', views.SiteViewSet, basename='site')

urlpatterns = [
    path('overview/', views.SiteOverview.as_view(), name='deployment-overview'),
]

urlpatterns += router.urls
