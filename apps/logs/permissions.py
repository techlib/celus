from core.models import DATA_SOURCE_TYPE_ORGANIZATION
from rest_framework.permissions import BasePermission


class AccessiblePlatformFromOrganization(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method == "POST":
            if organization_id := request.data.get("organization_id"):
                if (
                    obj.platform.source
                    and obj.platform.source.type == DATA_SOURCE_TYPE_ORGANIZATION
                    and obj.platform.source.organization.pk != organization_id
                ):
                    # Unrelated private platform
                    return False

        return True
