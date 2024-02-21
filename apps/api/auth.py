from typing import Optional

from organizations.models import Organization
from rest_framework_api_key.permissions import KeyParser

from api.models import OrganizationAPIKey


def extract_org_from_request_api_key(request) -> Optional[Organization]:
    key_parser = KeyParser()
    key = key_parser.get_from_authorization(request)
    if key:
        api_key = OrganizationAPIKey.objects.get_from_key(key)
        request._api_key = api_key
        return api_key.organization
    return None
