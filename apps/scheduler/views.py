from django.shortcuts import get_object_or_404

from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework import mixins, status
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet

from core.permissions import SuperuserOrAdminPermission
from core.models import REL_ORG_USER
from sushi.models import SushiCredentials, CounterReportsToCredentials

from .serializers import (
    FetchIntentionSerializer,
    RetrieveHarvestSerializer,
    CreateHarvestSerializer,
    ListHarvestSerializer,
)
from .models import FetchIntention, Harvest


class HarvestViewSetPagination(LimitOffsetPagination):
    default_limit = 100
    max_limit = 1000


class HarvestViewSet(
    mixins.RetrieveModelMixin, mixins.ListModelMixin, mixins.CreateModelMixin, GenericViewSet
):

    serializer_class = RetrieveHarvestSerializer
    pagination_class = HarvestViewSetPagination

    def get_queryset(self):
        if SuperuserOrAdminPermission().has_permission(self.request, self):
            qs = Harvest.objects.all()
        else:
            qs = Harvest.objects.filter(last_updated_by=self.request.user)

        qs = qs.order_by('-pk')

        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return ListHarvestSerializer
        elif self.action == 'retrieve':
            return RetrieveHarvestSerializer
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
                raise ValidationError(f'Credentials (pk={credentials.pk}) seems to be broken.')
            try:
                cr2c = credentials.counterreportstocredentials_set.get(
                    counter_report=intention["counter_report"]
                )
            except CounterReportsToCredentials.DoesNotExist:
                raise ValidationError(
                    f'Counter report type (pk={intention["counter_report"].pk}) is not set for Credentials (pk={credentials.pk})'
                )

            if cr2c.broken:
                raise ValidationError(
                    f'Counter report type (pk={intention["counter_report"].pk}) seems to be broken for credentials (pk={credentials.pk}).'
                )

    def create(self, request, *args, **kwargs):
        data = dict(request.data)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        # put created instance into response
        response_serialzer = RetrieveHarvestSerializer(serializer.instance)

        return Response(response_serialzer.data, status=status.HTTP_201_CREATED, headers=headers)


class IntentionViewSet(ReadOnlyModelViewSet):

    serializer_class = FetchIntentionSerializer

    def get_queryset(self):
        kwargs = {
            "pk": self.kwargs["harvest_pk"],
        }
        if not SuperuserOrAdminPermission().has_permission(self.request, self):
            kwargs["last_updated_by"] = self.request.user

        harvest = get_object_or_404(Harvest, **kwargs)
        return harvest.latest_intentions
