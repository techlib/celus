from collections import Counter

from core.logic.dates import month_end
from core.models import REL_ORG_USER
from core.permissions import SuperuserOrAdminPermission
from django.db.models import Count, F, Max, Min, Prefetch, Q
from django.db.models.functions import Coalesce
from django.db.transaction import atomic
from django.shortcuts import get_object_or_404
from django.utils import timezone
from logs.models import ImportBatch
from logs.views import StandardResultsSetPagination
from rest_framework import filters, mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.fields import DateField
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ReadOnlyModelViewSet
from sushi.models import (
    CounterReportsToCredentials,
    CounterReportType,
    SushiCredentials,
    SushiFetchAttempt,
)

from .filters import harvests as harvests_filters
from .filters import intentions as intentions_filters
from .models import Automatic, FetchIntention, Harvest
from .serializers import (
    CreateHarvestSerializer,
    DetailHarvestSerializer,
    FetchIntentionSerializer,
    FetchIntentionShortSerializer,
    ListHarvestSerializer,
)
from .tasks import trigger_scheduler


class HarvestViewSet(
    mixins.RetrieveModelMixin, mixins.ListModelMixin, mixins.CreateModelMixin, GenericViewSet
):

    pagination_class = StandardResultsSetPagination

    filter_backends = [
        harvests_filters.FinishedFilter,
        harvests_filters.BrokenFilter,
        harvests_filters.AutomaticFilter,
        harvests_filters.MonthFilter,
        harvests_filters.OrderingFilter,
    ]

    def get_queryset(self):
        if SuperuserOrAdminPermission().has_permission(self.request, self):
            qs = Harvest.objects.all()
        else:
            qs = Harvest.objects.filter(
                Q(last_updated_by=self.request.user)
                | Q(automatic__organization__in=self.request.user.admin_organizations())
            )

        # we need to add platform filter before we start annotating, because Django would then
        # create extra joins which make the query more than 10x slower
        if platforms := self.request.query_params.get('platforms', None):
            platforms = platforms.strip()
            if platforms:
                qs = qs.filter(intentions__credentials__platform_id__in=platforms.split(","))

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
                                    intentions__credentials__counterreportstocredentials__broken__isnull=False  # noqa E501
                                )
                                & Q(
                                    intentions__credentials__counterreportstocredentials__counter_report_id=F(  # noqa E501
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
            # we do not want to check the same organization more than once when many
            # intentions are created for the same organization
            seen_orgs = set()
            for intention in serializer.validated_data["intentions"]:
                org_id = intention["credentials"].organization_id
                # Check whether user is within organization - it is an ID now
                if (
                    org_id not in seen_orgs
                    and self.request.user.organization_relationship(org_id) < REL_ORG_USER
                ):
                    raise PermissionDenied(
                        f"No permission to use credentails (pk={intention['credentials'].pk})"
                    )
                seen_orgs.add(org_id)

        serializer.save(last_updated_by=self.request.user)
        # Test whether credentials are not broken
        # Because usually we harvest many months for a few credentials, we want to skip
        # validation for credentials that have already been validated
        # `seen_combinations` stores tuples of (credentials_id, counter_report_id)
        # that have been validated
        seen_combinations = set()
        for intention in serializer.validated_data["intentions"]:
            credentials = intention["credentials"]
            key = (intention['credentials'].pk, intention['counter_report'].pk)
            if key in seen_combinations:
                continue
            if credentials.broken:
                raise ValidationError({credentials.pk: 'Credentials are broken.'})
            try:
                cr2c = credentials.counterreportstocredentials_set.get(
                    counter_report=intention["counter_report"]
                )
            except CounterReportsToCredentials.DoesNotExist:
                raise ValidationError(
                    {
                        credentials.pk: f'Counter report {intention["counter_report"].code} '
                        f'is not active for credentials'
                    }
                )

            if cr2c.broken:
                raise ValidationError(
                    {
                        credentials.pk: f'Counter report {intention["counter_report"].code} '
                        f'is broken for credentials'
                    }
                )
            seen_combinations.add(key)

    def create(self, request, *args, **kwargs):
        data = dict(request.data)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        # put created instance into response
        response_serialzer = DetailHarvestSerializer(serializer.instance)

        return Response(response_serialzer.data, status=status.HTTP_201_CREATED, headers=headers)


class LastUpdatedIntentionFilterBackend(filters.BaseFilterBackend):
    """
    Filter that allows selection of intentions that have been updated since a given timestamp.
    Because the attempt may have changed without the intention being updated, we also check
    the attempt's last_updated field.
    """

    query_param = 'last_updated_after'

    def filter_queryset(self, request, queryset, view):
        if last_updated := request.query_params.get(self.query_param):
            queryset = queryset.filter(
                Q(last_updated__gt=last_updated) | Q(attempt__last_updated__gt=last_updated)
            )
        return queryset


class HarvestIntentionViewSet(ReadOnlyModelViewSet):

    serializer_class = FetchIntentionShortSerializer
    filter_backends = [LastUpdatedIntentionFilterBackend]

    def get_queryset(self):
        kwargs = {"pk": self.kwargs["harvest_pk"]}
        if not SuperuserOrAdminPermission().has_permission(self.request, self):
            kwargs["last_updated_by"] = self.request.user

        harvest = get_object_or_404(Harvest, **kwargs)

        if self.action == 'list' and not bool(self.request.query_params.get('list_all', False)):
            qs = harvest.latest_intentions
        else:
            qs = harvest.intentions

        return qs.select_related(
            'counter_report',
            'credentials',
            'credentials__platform',
            'credentials__organization',
            'duplicate_of',
            'current_scheduler',
            'previous_intention',
            'previous_intention__counter_report',
            'previous_intention__credentials__organization',
            'previous_intention__credentials__platform',
            'attempt',
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
    http_method_names = ['get', 'options', 'head', 'post']
    filter_backends = [
        intentions_filters.OrganizationFilter,
        intentions_filters.PlatformFilter,
        intentions_filters.ReportFilter,
        intentions_filters.DateFromFilter,
        intentions_filters.MonthFilter,
        intentions_filters.CounterVersionFilter,
        intentions_filters.ModeFilter,
        intentions_filters.OrderingFilter,
        intentions_filters.AttemptFilter,
        intentions_filters.CredentialsFilter,
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

    class PurgeSerializer(Serializer):
        credentials = PrimaryKeyRelatedField(many=False, queryset=SushiCredentials.objects.all())
        start_date = DateField()
        counter_report = PrimaryKeyRelatedField(
            many=False, queryset=CounterReportType.objects.all()
        )

    @atomic
    @action(detail=False, methods=['post'], serializer_class=PurgeSerializer)
    def purge(self, request):
        """Removes all intentions and related data"""
        stats = Counter()
        serializer = self.PurgeSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        for item in serializer.validated_data:
            credentials = item['credentials']
            start_date = item['start_date']
            counter_report = item['counter_report']
            if not request.user.has_organization_admin_permission(credentials.organization_id):
                raise PermissionDenied(
                    f'User not allowed to manage data for organization: '
                    f'{credentials.organization_id}'
                )
            to_delete = FetchIntention.objects.filter(
                credentials=credentials,
                start_date=start_date,
                end_date=month_end(start_date),
                counter_report=counter_report,
            )
            stats.update(
                ImportBatch.objects.filter(
                    sushifetchattempt__fetchintention__in=to_delete
                ).delete()[1]
            )
            stats.update(SushiFetchAttempt.objects.filter(fetchintention__in=to_delete).delete()[1])
            stats.update(to_delete.delete()[1])

        return Response(dict(stats))
