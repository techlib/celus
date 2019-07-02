from django.urls import path

from . import views

urlpatterns = [
    path('user/', views.UserView.as_view(), name='user_api_view'),
]
