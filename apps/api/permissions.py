from rest_framework_api_key.permissions import BaseHasAPIKey

from api.models import OrganizationAPIKey


class HasOrganizationAPIKey(BaseHasAPIKey):
    model = OrganizationAPIKey
