from api.models import OrganizationAPIKey
from rest_framework_api_key.permissions import BaseHasAPIKey


class HasOrganizationAPIKey(BaseHasAPIKey):
    model = OrganizationAPIKey
