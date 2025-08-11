from core.models import User
from django.db.models import Q
from organizations.models import UserOrganization
from rest_framework.permissions import BasePermission
from rest_framework.request import Request


# Should be used in CUSTOM_USER_QUERYSET settings value
def users_impersonable(request: Request):
    """Users which can be impersonated"""
    q = Q(is_superuser=False, is_active=True)

    orig_user = getattr(request, "real_user", request.user)
    if not (orig_user.is_superuser or orig_user.is_admin_of_master_organization):
        # impersonable users based on UserOrganization.can_impersonate flag
        orig_orgs = (
            UserOrganization.objects.filter(user=orig_user, can_impersonate=True)
            .values_list("organization", flat=True)
            .distinct()
        )
        if not orig_orgs:
            # short circuit if no organizations to impersonate
            return User.objects.none()
        candidates_u2o = UserOrganization.objects.filter(
            organization__in=orig_orgs,
            can_impersonate=False,
            user__is_active=True,
            user__is_superuser=False,
        ).select_related("user")
        candidate_ids = {
            e.user_id
            for e in candidates_u2o
            if not e.user.is_admin_of_master_organization
            and not e.user.is_superuser  # no consortial admins nor superusers
        }

        # we need to prevent possible privilege escalation
        # So we are going to check that all UserOrganizations relation
        # of newly impersonable users are subset of current user's organizations
        orig_u2o = UserOrganization.objects.filter(user=orig_user)
        orig_admin_orgs = {e.organization_id for e in orig_u2o if e.is_admin}
        orig_user_orgs = {e.organization_id for e in orig_u2o}
        u2o = UserOrganization.objects.filter(user__in=candidate_ids)
        filtered_user_ids = []
        for user_id in candidate_ids:
            admin_orgs = {e.organization_id for e in u2o if e.user_id == user_id and e.is_admin}
            user_orgs = {e.organization_id for e in u2o if e.user_id == user_id}
            if orig_admin_orgs.issuperset(admin_orgs) and orig_user_orgs.issuperset(user_orgs):
                filtered_user_ids.append(user_id)

        q = q & Q(pk__in=filtered_user_ids)

    if hasattr(request, "real_user"):
        # can impersonate back to original user
        q |= Q(pk=request.real_user.pk)

    return User.objects.filter(q)


# Should be used in CUSTOM_ALLOW settings value
def check_allow_impersonate(request: Request):
    """Checks whether the user can impersonate"""

    def check_user(user: User):
        if user.is_superuser:
            return True
        if getattr(user, "is_admin_of_master_organization", False):
            return user.is_admin_of_master_organization

        # note that can_impersonate implies is_admin
        return UserOrganization.objects.filter(user_id=user.pk, can_impersonate=True).exists()

    if check_user(request.user):
        return True
    else:
        if imp_user := request.impersonator:
            return check_user(imp_user)

    return False


class ImpersonatePermission(BasePermission):
    def has_permission(self, request, view):
        return check_allow_impersonate(request)

    def has_object_permission(self, request, view, obj):
        return check_allow_impersonate(request)
