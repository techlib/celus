import operator
from functools import reduce

from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from annotations.models import Annotation
from annotations.serializers import AnnotationSerializer
from core.logic.dates import parse_month, month_end
from core.permissions import OwnerLevelBasedPermissions, CanPostOrganizationDataPermission, \
    CanAccessOrganizationRelatedObjectPermission


class AnnotationsViewSet(ModelViewSet):

    queryset = Annotation.objects.all()
    serializer_class = AnnotationSerializer
    permission_classes = [IsAuthenticated &
                          OwnerLevelBasedPermissions &
                          CanPostOrganizationDataPermission &
                          CanAccessOrganizationRelatedObjectPermission]

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

