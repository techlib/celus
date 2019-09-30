import operator
from functools import reduce

from django.db.models import Q
from rest_framework.permissions import BasePermission, IsAuthenticated, SAFE_METHODS
from rest_framework.viewsets import ModelViewSet

from annotations.models import Annotation
from annotations.serializers import AnnotationSerializer
from core.logic.dates import parse_month, month_end
from core.logic.url import extract_organization_id_from_request
from core.models import REL_ORG_ADMIN, REL_UNREL_USER
from organizations.models import UserOrganization


class OwnerLevelBasedPermissions(IsAuthenticated):

    READ_PERMISSION_LEVEL = REL_UNREL_USER
    WRITE_PERMISSION_LEVEL = REL_ORG_ADMIN

    def has_permission(self, request, view):
        parent = super().has_permission(request, view)
        if not parent:
            # if the parent check was unsuccessful, we just pass it
            return False
        rel = request.user.request_relationship(request)
        if rel >= self.READ_PERMISSION_LEVEL:
            return True
        return False

    def has_object_permission(self, request, view, obj):
        parent = super().has_object_permission(request, view, obj)
        if not parent:
            return False
        rel = request.user.request_relationship(request)
        if rel >= self.WRITE_PERMISSION_LEVEL:
            if hasattr(obj, 'owner_level'):
                return rel >= obj.owner_level
            return True
        return False


class CanAccessOrganizationPermission(IsAuthenticated):

    PERMIT_NO_ORG_IN_SAFE_REQUEST = False  # allow safe access when no organization is specified?
    PERMIT_NO_ORG_IN_UNSAFE_REQUEST = False  # allow write access when no org is specified?
    PERMIT_NO_ORG_IN_SAFE_OBJECT_REQUEST = False  # same as above but on object level
    PERMIT_NO_ORG_IN_UNSAFE_OBJECT_REQUEST = False  # allow write access when no org is specified?

    def has_permission(self, request, view):
        parent = super().has_permission(request, view)
        if not parent:
            # if the parent check was unsuccessful, we just pass it
            return False
        if request.user.is_superuser or request.user.is_from_master_organization:
            return True
        org_id = extract_organization_id_from_request(request)
        if request.method in SAFE_METHODS:
            if org_id:
                return self.has_org_access(request.user, org_id)
            else:
                return self.PERMIT_NO_ORG_IN_SAFE_REQUEST
        else:
            if org_id:
                return self.has_org_admin(request.user, org_id)
            else:
                return self.PERMIT_NO_ORG_IN_UNSAFE_REQUEST

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            if hasattr(obj, 'organization_id'):
                return self.has_org_admin(request.user, obj.organization_id)
            else:
                return self.PERMIT_NO_ORG_IN_SAFE_OBJECT_REQUEST
        else:
            if hasattr(obj, 'organization_id'):
                return self.has_org_access(request.user, obj.organization_id)
            else:
                return self.PERMIT_NO_ORG_IN_UNSAFE_OBJECT_REQUEST

    def has_org_admin(self, user, org_id):
        if org_id:
            return UserOrganization.objects.\
                filter(user=user, organization_id=org_id, is_admin=True).exists()
        return False

    def has_org_access(self, user, org_id):
        return user.accessible_organizations().filter(pk=org_id).exists()


class CanAccessOrganizationPermissiveSafePermission(CanAccessOrganizationPermission):

    PERMIT_NO_ORG_IN_SAFE_REQUEST = True


class AnnotationsViewSet(ModelViewSet):

    queryset = Annotation.objects.all()
    serializer_class = AnnotationSerializer
    permission_classes = [OwnerLevelBasedPermissions,
                          CanAccessOrganizationPermissiveSafePermission]

    def get_queryset(self):
        org_perm_args = (Q(organization__in=self.request.user.accessible_organizations()) |
                         Q(organization__isnull=True))
        query_args = []
        exclude_args = []
        for param in ('platform', 'organization'):
            value = self.request.query_params.get(param)
            if value:
                # we filter to include those with specified value or with this value null
                query_args.append(Q(**{param+'_id': value}) | Q(**{param+'__isnull': True}))
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            exclude_args.append(Q(end_date__lte=parse_month(start_date)))
        if end_date:
            exclude_args.append(Q(start_date__gte=month_end(parse_month(end_date))))
        if len(exclude_args) > 1:
            # we have more args, we need to "OR" them
            exclude_args = [reduce(operator.or_, exclude_args)]
        return Annotation.objects.filter(org_perm_args).filter(*query_args).\
            exclude(*exclude_args).select_related('organization', 'platform')

