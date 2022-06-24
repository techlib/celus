from core.models import User
from django.db.models import Q
from rest_framework.permissions import BasePermission
from rest_framework.request import Request


# Should be used in CUSTOM_USER_QUERYSET settings value
def users_impersonable(request: Request):
    """ Users which can be impersonated """
    q = Q(is_superuser=False, is_active=True)

    if hasattr(request, 'real_user'):
        q |= Q(pk=request.real_user.pk)

    return User.objects.filter(q)


# Should be used in CUSTOM_ALLOW settings value
def check_allow_impersonate(request: Request):
    """ Checks whether the user can impersonate """

    def check_user(user: User):
        if user.is_superuser:
            return True
        if hasattr(user, "is_admin_of_master_organization"):
            return user.is_admin_of_master_organization
        return False

    if check_user(request.user):
        return True
    else:
        if imp_user := getattr(request, "impersonator"):
            return check_user(imp_user)
        else:
            return False


class ImpersonatedSuperuserOrAdminPermission(BasePermission):
    def has_permission(self, request, view):
        return check_allow_impersonate(request)

    def has_object_permission(self, request, view, obj):
        return check_allow_impersonate(request)
