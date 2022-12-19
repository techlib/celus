from django.db import models
from rest_framework_api_key.models import AbstractAPIKey


class OrganizationAPIKey(AbstractAPIKey):
    organization = models.ForeignKey(
        'organizations.Organization', on_delete=models.CASCADE, related_name='api_keys'
    )
