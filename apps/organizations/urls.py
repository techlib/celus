from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"organization", views.OrganizationViewSet, basename="organization")

urlpatterns = [
    path("run-task/erms-sync-organizations", views.StartERMSSyncOrganizationsTask.as_view()),
    path(
        "country-autocomplete", views.CountryAutocompleteView.as_view(), name="country-autocomplete"
    ),
    path("state-autocomplete", views.StateAutocompleteView.as_view(), name="state-autocomplete"),
]

urlpatterns += router.urls
