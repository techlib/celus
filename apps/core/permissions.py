from rest_framework.permissions import BasePermission, SAFE_METHODS

from core.logic.url import extract_organization_id_from_request_data
from core.models import REL_ORG_ADMIN, REL_UNREL_USER
from organizations.models import UserOrganization


class OwnerLevelBasedPermissions(BasePermission):

    """
    For models that have the 'owner_level' attribute checks that the current user has
    high enough privileges to modify that model.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if hasattr(obj, 'owner_level'):
            rel = request.user.organization_relationship(obj.organization_id)
            return rel >= obj.owner_level
        return True


class OrganizationRelatedPermissionMixin(object):

    """
    Base class for permissions that have to check if user is related to an organization and how
    """

    NO_DATA_METHODS = ('DELETE',)

    def has_org_admin(self, user, org_id):
        if user.is_superuser or user.is_from_master_organization:
            return True
        if org_id:
            return UserOrganization.objects.\
                filter(user=user, organization_id=org_id, is_admin=True).exists()
        return False

    def has_org_access(self, user, org_id):
        if not org_id:
            return True
        return user.accessible_organizations().filter(pk=org_id).exists()


class CanPostOrganizationDataPermission(OrganizationRelatedPermissionMixin, BasePermission):

    """
    Checks that organization sent in POST (and PUT and PATCH) data is accessible by the user
    """

    PERMIT_NO_ORG_IN_SAFE_REQUEST = True  # allow safe access when no organization is specified?
    PERMIT_NO_ORG_IN_UNSAFE_REQUEST = False  # allow write access when no org is specified?

    def has_permission(self, request, view):
        if request.user.is_superuser or request.user.is_from_master_organization:
            return True
        if request.method in self.NO_DATA_METHODS + SAFE_METHODS:
            return True  # we have nothing to check here
        org_id = extract_organization_id_from_request_data(request)
        if org_id:
            return self.has_org_admin(request.user, org_id)
        else:
            return self.PERMIT_NO_ORG_IN_UNSAFE_REQUEST


class CanAccessOrganizationRelatedObjectPermission(OrganizationRelatedPermissionMixin,
                                                   BasePermission):
    """
    Checks that object that is accessed is associated with an organization that the user
    can access
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser or request.user.is_from_master_organization:
            return True
        if request.method in SAFE_METHODS:
            return self.has_org_access(request.user, obj.organization_id)
        else:
            return self.has_org_admin(request.user, obj.organization_id)
