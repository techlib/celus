from typing import Optional

from api.models import OrganizationAPIKey
from organizations.models import Organization
from rest_framework_api_key.permissions import KeyParser


def extract_org_from_request_api_key(request) -> Optional[Organization]:
    key_parser = KeyParser()
    key = key_parser.get_from_authorization(request)
    if key:
        api_key = OrganizationAPIKey.objects.get_from_key(key)
        return api_key.organization
    return None
