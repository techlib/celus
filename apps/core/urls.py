from django.urls import path

from . import views

urlpatterns = [
    path('user/', views.UserView.as_view(), name='user_api_view'),
    path('user/language', views.UserLanguageView.as_view(), name='user_lang_api_view'),
    path(
        'user/verify-email', views.UserVerifyEmailView.as_view(), name='user_api_verify_email_view'
    ),
    path('info/', views.SystemInfoView.as_view(), name='system_info_api_view'),
    path(
        'run-task/erms-sync-users-and-identities',
        views.StartERMSSyncUsersAndIdentitiesTask.as_view(),
    ),
    path('test-email/', views.TestEmailView.as_view(), name='test_email_api_view'),
    path('test-error/', views.TestErrorView.as_view(), name='test_error_api_view'),
]
