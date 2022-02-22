from collections import Counter

from django.core.exceptions import BadRequest
from django.db.models import Count, Exists, F, Max, Min, Prefetch, Q
from django.db.models.functions import Coalesce
from django.db.transaction import atomic
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.fields import DateField
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet, ModelViewSet

from core.logic.dates import parse_month, month_end
from core.models import REL_ORG_USER, REL_ORG_ADMIN
from core.permissions import SuperuserOrAdminPermission
from logs.models import ImportBatch
from logs.views import StandardResultsSetPagination
from sushi.models import (
    CounterReportsToCredentials,
    SushiFetchAttempt,
    SushiCredentials,
    CounterReportType,
)

from . import filters
from .models import Automatic, FetchIntention, Harvest
from .tasks import trigger_scheduler
from .serializers import (
    CreateHarvestSerializer,
    DetailHarvestSerializer,
    FetchIntentionSerializer,
    ListHarvestSerializer,
)


class HarvestViewSet(
    mixins.RetrieveModelMixin, mixins.ListModelMixin, mixins.CreateModelMixin, GenericViewSet
):

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
                    queryset=FetchIntention.objects.latest_intentions().annotate_credentials_state(),
                    to_attr='prefetched_latest_intentions',
                ),
                Prefetch(
                    'intentions',
                    queryset=FetchIntention.objects.all().select_related(
                        'credentials__platform',
                        'credentials__platform__source',
                        'credentials__organization',
                    ),
                    to_attr='intentions_credentials',
                ),
            )
            .annotate(
                last_attempt_date=Max(
                    'intentions__not_before', filter=Q(intentions__duplicate_of__isnull=True)
                ),
                last_processed=Max('intentions__when_processed'),
                start_date=Min('intentions__start_date'),
                end_date=Max('intentions__end_date'),
                broken=Coalesce(
                    Count(
                        'intentions',
                        filter=(
                            Q(intentions__credentials__broken__isnull=False)
                            | (
                                Q(
                                    intentions__credentials__counterreportstocredentials__broken__isnull=False
                                )
                                & Q(
                                    intentions__credentials__counterreportstocredentials__counter_report_id=F(
                                        'intentions__counter_report'
                                    )
                                )
                            )
                        )
                        & Q(
                            intentions__when_processed__isnull=True
                        ),  # broken that hasn't been downloaded yet
                        distinct=True,
                    ),
                    0,
                ),
            )
        )

        finished = self.request.query_params.get('finished', None)
        if finished == "1":
            qs = qs.filter(planned=0)
        elif finished == "0":
            qs = qs.filter(planned__gt=0)

        broken = self.request.query_params.get('broken', None)
        if broken == "1":
            qs = qs.filter(broken__gt=0)
        elif broken == "0":
            qs = qs.filter(broken=0)

        automatic = self.request.query_params.get('automatic', None)
        if automatic == "1":
            qs = qs.filter(automatic__isnull=False)
        elif automatic == "0":
            qs = qs.filter(automatic__isnull=True)

        month = self.request.query_params.get('month', None)
        if month:
            parsed_month = parse_month(month)
            qs = qs.filter(start_date__lte=parsed_month, end_date__gte=parsed_month)

        order_by = self.request.query_params.get('order_by', 'pk')
        order_desc = "desc" if self.request.query_params.get('desc', 'false') == 'true' else "asc"
        if order_by not in (
            'created',
            'pk',
            'automatic',
            'finished',
            'last_attempt_date',
            'attempt_count',
            'start_date',
            'last_processed',
        ):
            order_by = 'pk'
        qs = qs.order_by(getattr(F(order_by), order_desc)(nulls_last=True))

        # skip empty harvests
        qs = qs.filter(total__gt=0)

        return qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DetailHarvestSerializer
        if self.action == 'list':
            return ListHarvestSerializer
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
        response_serialzer = DetailHarvestSerializer(serializer.instance)

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

        return qs.select_related(
            'current_scheduler',
            'previous_intention',
            'previous_intention__counter_report',
            'previous_intention__credentials__organization',
            'previous_intention__credentials__platform',
            'attempt',
            'previous_intention__attempt',
            'previous_intention__attempt',
        ).order_by('pk')

    @action(methods=["POST"], detail=True, url_path='trigger')
    def trigger(self, request, pk, harvest_pk):
        intention = self.get_queryset().get(pk=pk)
        if intention.is_processed:
            return Response(
                data={"error": f"intention {pk} was already processed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        intention.not_before = timezone.now()
        intention.priority = FetchIntention.PRIORITY_NOW
        intention.save()

        # Plan scheduler triggering so that it start processing intentions right now
        trigger_scheduler.delay(intention.credentials.url, True)

        return Response(status=status.HTTP_200_OK)

    @action(methods=["POST"], detail=True, url_path='cancel')
    def cancel(self, request, pk, harvest_pk):
        intention = self.get_queryset().get(pk=pk)
        if not intention.cancel():
            return Response(
                data={"error": f"intention {pk} can't be canceled"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_200_OK)


class IntentionViewSet(ModelViewSet):

    serializer_class = FetchIntentionSerializer
    http_method_names = ['get', 'options', 'head']
    filter_backends = [
        filters.OrganizationFilter,
        filters.PlatformFilter,
        filters.ReportFilter,
        filters.DateFromFilter,
        filters.MonthFilter,
        filters.CounterVersionFilter,
        filters.ModeFilter,
        filters.OrderingFilter,
        filters.AttemptFilter,
        filters.CredentialsFilter,
    ]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return (
            FetchIntention.objects.all()
            .select_related(
                'attempt',
                'counter_report',
                'credentials__organization',
                'credentials__platform',
                'current_scheduler',
            )
            .annotate_credentials_state()
        )

    def filter_queryset(self, *args, **kwargs):
        if 'pk' in self.kwargs:
            # when a specific object was requested, do not filter for latest intentions to avoid
            # 404 for existing but not last intentions
            return super().filter_queryset(*args, **kwargs)
        return super().filter_queryset(*args, **kwargs).latest_intentions()
