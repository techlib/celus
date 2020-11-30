from django.db.models import Q, Exists, OuterRef, Prefetch, Max
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet

from core.models import REL_ORG_USER
from core.permissions import SuperuserOrAdminPermission
from logs.views import StandardResultsSetPagination
from sushi.models import CounterReportsToCredentials
from .models import Automatic, FetchIntention, Harvest
from .serializers import (
    FetchIntentionSerializer,
    CreateHarvestSerializer,
    HarvestSerializer,
)


class HarvestViewSet(
    mixins.RetrieveModelMixin, mixins.ListModelMixin, mixins.CreateModelMixin, GenericViewSet
):

    serializer_class = HarvestSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        if SuperuserOrAdminPermission().has_permission(self.request, self):
            qs = Harvest.objects.all()
        else:
            qs = Harvest.objects.filter(
                Q(last_updated_by=self.request.user)
                | Q(automatic__organization__in=self.request.user.admin_organizations())
            )

        qs = (
            qs.annotate_stats()
            .prefetch_related(
                Prefetch('automatic', queryset=Automatic.objects.select_related('organization')),
                Prefetch(
                    'intentions',
                    queryset=FetchIntention.objects.latest_intentions(
                        within_harvest=True
                    ).annotate_credentials_state(),
                    to_attr='prefetched_latest_intentions',
                ),
                Prefetch(
                    'intentions',
                    queryset=FetchIntention.objects.all().select_related(
                        'credentials__platform', 'credentials__organization'
                    ),
                    to_attr='intentions_credentials',
                ),
            )
            .annotate(
                last_attempt_date=Max(
                    'intentions__not_before', filter=Q(intentions__duplicate_of__isnull=True)
                )
            )
        )

        finished = self.request.query_params.get('finished', None)
        unprocessed_intention_query = FetchIntention.objects.filter(
            harvest=OuterRef('pk'), when_processed__isnull=True, duplicate_of__isnull=True,
        )
        if finished == "1":
            qs = qs.filter(~Exists(unprocessed_intention_query))
        elif finished == "0":
            qs = qs.filter(Exists(unprocessed_intention_query))

        order_by = self.request.query_params.get('order_by', 'pk')
        order_desc = self.request.query_params.get('desc', 'false') == 'true'
        if order_by not in ('created', 'pk', 'automatic', 'finished', 'last_attempt_date'):
            order_by = 'pk'
        if order_desc:
            order_by = '-' + order_by
        qs = qs.order_by(order_by)

        return qs

    def get_serializer_class(self):
        if self.action in ['retrieve', 'list']:
            return HarvestSerializer
        elif self.action == 'create':
            return CreateHarvestSerializer
        else:
            raise NotImplementedError

    def perform_create(self, serializer):
        # Permission checking
        # skip for superusers or masters
        if not SuperuserOrAdminPermission().has_permission(self.request, self):
            # Check organization permissions
            for intention in serializer.validated_data["intentions"]:
                organization = intention["credentials"].organization
                # Check whether user is within organization
                if self.request.user.organization_relationship(organization.pk) < REL_ORG_USER:
                    raise PermissionDenied(
                        f"No permission to use credentails (pk={intention['credentials'].pk})"
                    )

        # Test whether credentials are not broken
        serializer.save(last_updated_by=self.request.user)
        for intention in serializer.validated_data["intentions"]:
            credentials = intention["credentials"]
            if credentials.broken:
                raise ValidationError({credentials.pk: f'Credentials are broken.'})
            try:
                cr2c = credentials.counterreportstocredentials_set.get(
                    counter_report=intention["counter_report"]
                )
            except CounterReportsToCredentials.DoesNotExist:
                raise ValidationError(
                    {
                        credentials.pk: f'Counter report {intention["counter_report"].code} is not active for'
                        f' credentials'
                    }
                )

            if cr2c.broken:
                raise ValidationError(
                    {
                        credentials.pk: f'Counter report {intention["counter_report"].code} is broken for credentials'
                    }
                )

    def create(self, request, *args, **kwargs):
        data = dict(request.data)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        # put created instance into response
        response_serialzer = HarvestSerializer(serializer.instance)

        return Response(response_serialzer.data, status=status.HTTP_201_CREATED, headers=headers)


class HarvestIntentionViewSet(ReadOnlyModelViewSet):

    serializer_class = FetchIntentionSerializer

    def get_queryset(self):
        kwargs = {
            "pk": self.kwargs["harvest_pk"],
        }
        if not SuperuserOrAdminPermission().has_permission(self.request, self):
            kwargs["last_updated_by"] = self.request.user

        harvest = get_object_or_404(Harvest, **kwargs)

        if self.action == 'list' and not bool(self.request.query_params.get('list_all', False)):
            qs = harvest.latest_intentions
        else:
            qs = harvest.intentions

        return qs.select_related('current_scheduler').order_by('pk')


class IntentionViewSet(ReadOnlyModelViewSet):

    serializer_class = FetchIntentionSerializer

    def get_queryset(self):
        org_perm_args = [
            Q(credentials__organization__in=self.request.user.accessible_organizations())
        ]
        return FetchIntention.objects.filter(*org_perm_args)
