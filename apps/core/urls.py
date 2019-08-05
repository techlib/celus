from django.urls import path

from . import views

urlpatterns = [
    path('user/', views.UserView.as_view(), name='user_api_view'),
    path('user/language', views.UserLanguageView.as_view(), name='user_api_view'),
]
