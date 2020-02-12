from rest_framework.permissions import BasePermission, SAFE_METHODS

from core.logic.url import extract_organization_id_from_request_data
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

    @classmethod
    def has_org_admin(cls, user, org_id):
        if org_id:
            return UserOrganization.objects.\
                filter(user=user, organization_id=org_id, is_admin=True).exists()
        return False

    @classmethod
    def has_org_access(cls, user, org_id):
        if not org_id:
            return True
        return user.accessible_organizations().filter(pk=org_id).exists()


class CanPostOrganizationDataPermission(OrganizationRelatedPermissionMixin, BasePermission):

    """
    Checks that organization sent in POST (and PUT and PATCH) data is accessible by the user
    """

    def has_permission(self, request, view):
        if request.method in self.NO_DATA_METHODS + SAFE_METHODS:
            return True  # we have nothing to check here
        org_id, key_present = extract_organization_id_from_request_data(request)
        if org_id:
            return self.has_org_admin(request.user, org_id)
        return True


class CanAccessOrganizationRelatedObjectPermission(OrganizationRelatedPermissionMixin,
                                                   BasePermission):
    """
    Checks that object that is accessed is associated with an organization that the user
    can access
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return self.has_org_access(request.user, obj.organization_id)
        else:
            return self.has_org_admin(request.user, obj.organization_id)


class CanAccessOrganizationFromGETAttrs(OrganizationRelatedPermissionMixin,
                                        BasePermission):
    """
    Checks that object the user has access to the organization present in the GET params
    """

    def has_permission(self, request, view):
        organization = request.GET.get('organization')
        if organization is None:
            return False
        if organization == '-1':
            return request.user.is_superuser or request.user.is_from_master_organization
        else:
            return request.user.accessible_organizations().\
                filter(organization_id=organization).exists()


class OrganizationRequiredInDataForNonSuperusers(BasePermission):

    FULL_DATA_METHODS = ('POST', 'PUT')

    def has_permission(self, request, view):
        ord_id, key_present = extract_organization_id_from_request_data(request)
        if request.method in self.FULL_DATA_METHODS:
            if not ord_id:
                return False
        elif key_present and not ord_id:
            # e.g. for PATCH if the key is present, it must hold a value
            # if it is not in the data, we do not care
            return False
        return True


class SuperuserOrAdminPermission(BasePermission):

    def has_permission(self, request, view):
        if request.user.is_superuser or (hasattr(request.user, 'is_from_master_organization') and
                                         request.user.is_from_master_organization):
            return True
        return False

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser or request.user.is_from_master_organization:
            return True
        return False


class SuperuserPermission(BasePermission):

    def has_permission(self, request, view):
        return request.user.is_superuser

    def has_object_permission(self, request, view, obj):
        return request.user.is_superuser
