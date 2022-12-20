import operator
from functools import reduce

from annotations.models import Annotation, Validity
from annotations.serializers import AnnotationSerializer
from core.logic.dates import month_end, parse_month
from core.models import UL_CONS_STAFF, UL_NORMAL
from core.permissions import (
    CanAccessOrganizationRelatedObjectPermission,
    CanPostOrganizationDataPermission,
    OrganizationRequiredInDataForNonSuperusers,
    OwnerLevelBasedPermissions,
    SuperuserOrAdminPermission,
)
from django.db.models import Q
from logs.views import StandardResultsSetPagination
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet


class AnnotationsViewSet(ModelViewSet):

    queryset = Annotation.objects.all()
    serializer_class = AnnotationSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter]
    search_fields = [
        'subject',
        'short_message',
        'message',
        'author__first_name',
        'author__last_name',
        'author__email',
    ]

    permission_classes = [
        IsAuthenticated
        & (
            (SuperuserOrAdminPermission & OwnerLevelBasedPermissions)
            | (
                OwnerLevelBasedPermissions
                & CanPostOrganizationDataPermission
                & CanAccessOrganizationRelatedObjectPermission
                & OrganizationRequiredInDataForNonSuperusers
            )
        )
    ]

    def paginate_queryset(self, queryset, view=None):
        if 'no_page' in self.request.query_params:
            return None
        else:
            return self.paginator.paginate_queryset(queryset, self.request, view=self)

    def get_queryset(self):
        params = self.request.query_params
        org_perm_args = Q(organization__in=self.request.user.accessible_organizations()) | Q(
            organization__isnull=True
        )
        query_args = []
        exclude_args = []
        for param in ('platform', 'organization'):
            value = params.getlist(param + '[]') or params.get(param)
            if value:
                if value == 'null':
                    # only those with the value equal to None are requested
                    query_args.append(Q(**{param + '__isnull': True}))
                else:
                    # we filter to include those with specified value or with this value null
                    param_id = f'{param}_id__in' if isinstance(value, list) else f'{param}_id'
                    query_args.append(Q(**{param_id: value}) | Q(**{param + '__isnull': True}))
        start_date = params.get('start_date')
        end_date = params.get('end_date')
        if start_date:
            exclude_args.append(Q(end_date__lte=parse_month(start_date)))
        if end_date:
            exclude_args.append(Q(start_date__gte=month_end(parse_month(end_date))))
        if len(exclude_args) > 1:
            # we have more args, we need to "OR" them
            exclude_args = [reduce(operator.or_, exclude_args)]

        if params.get("validity"):
            query_args.append(Validity(params.get("validity")).as_query())

        ordering = params.getlist('ordering[]') or ['pk']
        qs = (
            Annotation.objects.filter(org_perm_args)
            .filter(*query_args)
            .exclude(*exclude_args)
            .select_related('organization', 'platform', 'author')
            .order_by(*ordering)
        )
        # add access level stuff
        org_to_level = {}
        user = self.request.user
        for annot in qs:  # type: Annotation
            if not annot.organization_id:
                user_org_level = (
                    UL_CONS_STAFF
                    if user.is_superuser or user.is_admin_of_master_organization
                    else UL_NORMAL
                )
            else:
                if annot.organization_id not in org_to_level:
                    org_to_level[
                        annot.organization_id
                    ] = self.request.user.organization_relationship(annot.organization_id)
                user_org_level = org_to_level[annot.organization_id]
            annot.can_edit = user_org_level >= annot.owner_level
        return qs
