from collections import defaultdict

import reversion
from celus_nigiri.utils import parse_date_fuzzy
from core.logic.dates import month_end, month_start
from core.logic.type_conversion import to_bool
from core.models import UL_CONS_STAFF
from core.permissions import SuperuserOrAdminPermission
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db import transaction
from django.db.models import BooleanField, Count, F, Min, Prefetch, Q, Sum
from django.db.models.functions import Cast, Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from logs.models import ImportBatch
from logs.views import StandardResultsSetPagination
from organizations.logic.queries import organization_filter_from_org_id
from organizations.models import Organization
from publications.models import Platform
from publications.serializers import PlatformSerializer
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from reversion.views import create_revision
from scheduler.models import FetchIntention
from scheduler.serializers import MonthOverviewSerializer

from sushi.tasks import delete_credentials_task

from . import filters
from .logic.export import CredentialsDataFrame, OrganizationsDataFrame, Sheet, XlsxFile
from .models import (
    AttemptStatus,
    CounterReportPlatform,
    CounterReportsToCredentials,
    CounterReportType,
    CounterVersionChoices,
    DeleteCredentials,
    SushiCredentials,
)
from .serializers import (
    CloneToNewerSerializer,
    CounterReportTypeSerializer,
    SimpleSushiCredentialsSerializer,
    SushiCredentialsDataSerializer,
    SushiCredentialsListFilterSerializers,
    SushiCredentialsListSerializer,
    SushiCredentialsNoSameGlobalSerializer,
    SushiCredentialsNoSameInOrgSerializer,
    SushiCredentialsSerializer,
    SwitchToPlatformsReportTypesSerializer,
    UnsetBrokenSerializer,
    UpdateEnabledSerializer,
    UpdateLastHarvestableMonthSerializer,
)


class SushiCredentialsPagination(StandardResultsSetPagination):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.platforms = []
        self.stats = {}

    def get_page_size(self, request):
        if page_size := getattr(self, "_forced_page_size", None):
            return page_size
        else:
            return super().get_page_size(request)

    def paginate_queryset(self, queryset, request, view=None):
        # Return all credentials when `page` attr is missing
        # It is required because Some UI components expect unpaginated response
        if "page" not in request.query_params:
            self._forced_page_size = queryset.count()

        # Platforms were extracted in the view
        # Note that platform filter is ignored => should return the list of platforms
        # as if the platform filter was not used
        self.platforms = getattr(view, "_extracted_platforms", [])

        res = super().paginate_queryset(queryset, request, view)

        self.stats = queryset.annotate(
            counter_report_count=Count("counterreportstocredentials")
        ).aggregate(
            inactive_count=Count("pk", filter=Q(enabled=False)),
            broken_count=Count("pk", filter=Q(broken__isnull=False)),
            broken_report_count=Coalesce(Sum("counter_report_broken_count"), 0),
            report_count=Coalesce(Sum("counter_report_count"), 0),
            report_from_broken_credentials_count=Coalesce(
                Sum("counter_report_count", filter=Q(broken__isnull=False)), 0
            ),
            report_from_inactive_credentials_count=Coalesce(
                Sum("counter_report_count", filter=Q(enabled=False)), 0
            ),
        )

        if not getattr(view, "is_simple", False):
            # It is not necessary to annotate_verified for simple views
            ids = [rec.pk for rec in res]
            res = queryset.annotate_verified().filter(pk__in=ids)

        return res

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count if data else 0,
                "platforms": self.platforms,
                "results": data,
                "inactive_count": self.stats.get("inactive_count", 0),
                "broken_count": self.stats.get("broken_count", 0),
                "broken_report_count": self.stats.get("broken_report_count", 0),
                "report_count": self.stats.get("report_count", 0),
                "report_from_broken_credentials_count": self.stats.get(
                    "report_from_broken_credentials_count", 0
                ),
                "report_from_inactive_credentials_count": self.stats.get(
                    "report_from_inactive_credentials_count", 0
                ),
            }
        )


class SushiCredentialsViewSet(ModelViewSet):
    pagination_class = SushiCredentialsPagination
    queryset = SushiCredentials.objects.none()
    filter_backends = [
        SearchFilter,
        OrderingFilter,
        filters.CredentialsPlatformFilter,
        filters.CredentialsCounterVersionFilter,
        filters.CredentialsLastHarvestableMonthFilter,
        filters.CredentialsPotentialIssuesFilter,
        filters.CredentialsEnabledFilter,
    ]
    search_fields = ["title", "platform__name", "platform__short_name", "organization__name"]
    ordering = ["organization__name", "platform__name", "-counter_version"]
    ordering_fields = [
        "title",
        "organization__name",
        "platform__name",
        "counter_version",
        "enabled",
        "outside_consortium",
        "lock_level",
    ]

    @property
    def is_simple(self):
        return to_bool(self.request.query_params.get("simple", "false"))

    def _post_process_queryset(self, qs):
        org_to_level = {}
        sc: SushiCredentials
        for sc in qs:
            if sc.organization_id not in org_to_level:
                org_to_level[sc.organization_id] = self.request.user.organization_relationship(
                    sc.organization_id
                )
            user_org_level = org_to_level[sc.organization_id]
            if user_org_level >= sc.lock_level:
                sc.locked_for_me = False
            else:
                sc.locked_for_me = True
            if user_org_level >= UL_CONS_STAFF:
                sc.can_lock = True
            else:
                sc.can_lock = False
        return qs

    def get_queryset(self):
        user_organizations = self.request.user.admin_organizations()
        qs = SushiCredentials.objects.filter(
            organization__in=user_organizations, to_delete=DeleteCredentials.NO
        )
        organization_id = self.request.query_params.get("organization")
        if organization_id:
            qs = qs.filter(
                **organization_filter_from_org_id(
                    organization_id, self.request.user, admin_required=True
                )
            )
        qs = (
            qs.annotate_same_counts()
            .annotate_can_update()
            .annotate_has_51_provider()
            .annotate_any_broken()
            .prefetch_related("counterreportstocredentials_set__counter_report")
            .prefetch_related("platform__counterreportplatform_set__counter_report")
            .select_related(
                "organization",
                "platform",
                "platform__source",
                "platform__source__organization",
                "last_updated_by",
            )
        )
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            if self.is_simple:
                return SimpleSushiCredentialsSerializer
            else:
                return SushiCredentialsListSerializer

        forced = self.request.data.get("forced", False)
        if not forced:
            if settings.CONSORTIAL_INSTALLATION:
                return SushiCredentialsNoSameGlobalSerializer
            else:
                return SushiCredentialsNoSameInOrgSerializer

        return SushiCredentialsSerializer

    def list(self, request, *args, **kwargs):
        """
        We need to post-process queryset to add info about locked status for current user
        """
        SushiCredentialsListFilterSerializers(data=request.query_params).is_valid(
            raise_exception=True
        )
        queryset = self.filter_queryset(self.get_queryset())

        if "platform" in request.query_params:
            # We need to extract platforms without platform filter
            self._suppress_platform_filter = True
            platform_qs = self.filter_queryset(self.get_queryset())
        else:
            platform_qs = queryset

        platform_ids = platform_qs.values_list("platform_id", flat=True).distinct()
        platforms = (
            Platform.objects.filter(pk__in=platform_ids)
            .select_related("source", "source__organization")
            .prefetch_related(
                Prefetch(
                    "counterreportplatform_set",
                    queryset=CounterReportPlatform.objects.select_related("counter_report"),
                )
            )
        )

        self._extracted_platforms = PlatformSerializer(platforms, many=True).data

        qs = self.paginate_queryset(queryset)
        if qs:
            self._post_process_queryset(qs)
        serializer = self.get_serializer(qs or [], many=True)
        return self.get_paginated_response(serializer.data)

    @method_decorator(create_revision())
    def update(self, request, *args, **kwargs):
        reversion.set_comment("Updated through API")
        super().update(request, *args, **kwargs)
        instance = self.get_object()

        # Need to update verified status so it is up-to-date
        instance.verified = instance.is_verified
        self._post_process_queryset([instance])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @method_decorator(create_revision())
    def create(self, request, *args, **kwargs):
        reversion.set_comment("Created through API")
        return super().create(request, *args, **kwargs)

    @method_decorator(create_revision())
    def destroy(self, request, *args, **kwargs):
        delete_data = self.request.query_params.get("delete_data", "false").lower() == "true"
        credentials: SushiCredentials = self.get_object()
        if credentials.can_edit(request.user):
            if delete_data:
                credentials.to_delete = DeleteCredentials.WITH_DATA
                reversion.set_comment(
                    "Marked for deletion through API with all related FetchAttempts and "
                    "ImportBatches."
                )
            else:
                credentials.to_delete = DeleteCredentials.WITHOUT_DATA
                reversion.set_comment("Marked for deletion through API")
            credentials.save()
            transaction.on_commit(lambda: delete_credentials_task.delay(credentials.pk))
            return Response(status=status.HTTP_202_ACCEPTED)
        else:
            raise PermissionDenied("User is not allowed to delete this object")

    @action(detail=True, methods=["post"], permission_classes=[SuperuserOrAdminPermission])
    def lock(self, request, pk=None):
        """
        Custom action to lock the SushiCredentials
        """
        credentials = get_object_or_404(SushiCredentials, pk=pk)
        owner_level = request.user.organization_relationship(credentials.organization_id)
        requested_level = request.data.get("lock_level", owner_level)
        credentials.change_lock(request.user, requested_level)
        return Response(
            {
                "ok": True,
                "lock_level": credentials.lock_level,
                "locked": credentials.lock_level >= UL_CONS_STAFF,
            }
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="unset-broken",
        serializer_class=UnsetBrokenSerializer,
    )
    def unset_broken(self, request):
        """
        Custom action to unset that SushiCredentials are broken
        """

        request_serializer = UnsetBrokenSerializer(data=request.data, many=True)
        request_serializer.is_valid(raise_exception=True)
        # For some reason we need to revalidate every item
        # otherwise no exception is raise when invalid counter_report is provided
        for e in request.data:
            UnsetBrokenSerializer(data=e).is_valid(raise_exception=True)

        credentials_ids = [e["credentials_id"] for e in request_serializer.validated_data]
        credentials_map = {e.pk: e for e in SushiCredentials.objects.filter(pk__in=credentials_ids)}
        cr2c_map = defaultdict(list)
        for cr2c in CounterReportsToCredentials.objects.filter(
            broken__isnull=False, credentials_id__in=credentials_ids
        ):
            cr2c_map[cr2c.credentials_id].append(cr2c)

        with transaction.atomic():
            for credentials_dict in request_serializer.validated_data:
                if not (credentials := credentials_map.get(credentials_dict["credentials_id"])):
                    # skip credentials which doesn't exist
                    continue
                if "counter_reports" in credentials_dict:
                    for rt in credentials_dict["counter_reports"]:
                        for cr2c in cr2c_map.get(credentials_dict["credentials_id"]):
                            if cr2c.counter_report == rt:
                                cr2c.unset_broken()
                else:
                    credentials.unset_broken()
                    for cr2c in cr2c_map.get(credentials_dict["credentials_id"], []):
                        cr2c.unset_broken()
            qs = self._post_process_queryset(
                SushiCredentials.objects.filter(pk__in=credentials_ids)
            )
            return Response(SushiCredentialsSerializer(qs, many=True).data)

    @action(
        detail=False,
        methods=["post"],
        url_path="update-enabled",
        serializer_class=UpdateEnabledSerializer,
    )
    def update_enabled(self, request):
        """
        Custom action to update enabled (automatic harvesting)
        """
        request_serializer = UpdateEnabledSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        enabled = request_serializer.validated_data["enabled"]
        updated = SushiCredentials.objects.filter(
            enabled=not enabled, pk__in=request_serializer.validated_data["credentials"]
        ).update(enabled=enabled)

        return Response({"updated": updated})

    @action(
        detail=False,
        methods=["post"],
        url_path="clone-to-newer",
        serializer_class=CloneToNewerSerializer,
    )
    def clone_to_newer(self, request):
        request_serializer = CloneToNewerSerializer(data=request.data, many=True)
        request_serializer.is_valid(raise_exception=True)
        credentials_ids = [e["credentials_id"] for e in request_serializer.validated_data]
        creds = list(
            self._post_process_queryset(
                SushiCredentials.objects.filter(pk__in=credentials_ids)
                .annotate_can_update()
                .filter(can_update=True)
                .prefetch_related("counter_reports")
            )
        )

        result = []
        crt_mapping = CounterReportType.get_mapping()
        for cred in creds:
            if new_creds := cred.clone_to_c51(crt_mapping):
                result.append(new_creds)

        return Response(SushiCredentialsSerializer(result, many=True).data)

    @action(detail=False, methods=["post", "get"], url_path="export-credentials")
    def export_credentials(self, request):
        pks = request.data.getlist("pk")
        selected_organization_id = request.GET.get("organization", "-1")
        qs = self.get_queryset()
        if pks:
            qs = qs.filter(pk__in=pks)
        qs = qs.prefetch_related("counter_reports")
        sheets = [
            Sheet(
                CredentialsDataFrame.export(counter_version=51).create(qs), "Credentials-COUNTER5.1"
            ),
            Sheet(
                CredentialsDataFrame.export(counter_version=5).create(qs), "Credentials-COUNTER5"
            ),
            Sheet(
                CredentialsDataFrame.export(counter_version=4).create(qs), "Credentials-COUNTER4"
            ),
        ]
        excel_file = XlsxFile.new(sheets).create()
        response = HttpResponse(
            excel_file.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        today = now().strftime("%Y-%m-%d")
        org_suffix = (
            "consortium"
            if selected_organization_id == "-1"
            else Organization.objects.get(id=selected_organization_id).short_name
        )
        org_suffix = org_suffix.replace("/", "_")
        response["Content-Disposition"] = (
            f'attachment; filename="SushiCredentials-{today}_{org_suffix}.xlsx"'
        )
        return response

    @action(
        detail=False,
        methods=["post"],
        url_path="update-last-harvestable-month",
        serializer_class=UpdateLastHarvestableMonthSerializer,
    )
    def update_last_harvestable_month(self, request):
        serializer = UpdateLastHarvestableMonthSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        creds_map = SushiCredentials.objects.in_bulk()

        with transaction.atomic():
            updated_count = 0
            unmatched_count = 0
            matched_count = 0
            for record in serializer.validated_data:
                if creds := creds_map.get(record["credentials_id"]):
                    if not creds.can_edit(request.user):
                        raise PermissionDenied(
                            f"User #{request.user.pk} can't edit credentials "
                            f"#{record['credentials_id']}"
                        )
                    matched_count += 1
                    if creds.update_last_harvestable_month_by_user(
                        request.user, record["last_harvestable_month"]
                    ):
                        updated_count += 1
                else:
                    unmatched_count += 1

        return Response(
            {"matched": matched_count, "updated": updated_count, "unmatched": unmatched_count}
        )

    @action(detail=False, methods=["get"], url_name="import-template", url_path="import-template")
    def get_template_for_import(self, request):
        selected_organization_id = request.GET.get("organization", "-1")
        accessible_organizations = request.user.accessible_organizations()
        if selected_organization_id != "-1":
            accessible_organizations = accessible_organizations.filter(pk=selected_organization_id)
        admin_organizations = request.user.admin_organizations()
        qs = self.get_queryset()
        qs = qs.prefetch_related("counter_reports")
        sheets = [
            Sheet(
                CredentialsDataFrame.template_for_import(
                    selected_organization_id, CounterVersionChoices.C51
                ).create(qs, accessible_organizations),
                "Credentials-COUNTER5.1",
            ),
            Sheet(
                CredentialsDataFrame.template_for_import(
                    selected_organization_id, CounterVersionChoices.C5
                ).create(qs, accessible_organizations),
                "Credentials-COUNTER5",
            ),
        ]
        if selected_organization_id == "-1":
            sheets.append(
                Sheet(OrganizationsDataFrame(admin_organizations).create(), "Organizations")
            )
        excel_file = XlsxFile.use_template(sheets, selected_organization_id).create(
            mode="a", if_sheet_exists="overlay"
        )
        response = HttpResponse(
            excel_file.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        org_suffix = (
            "consortium"
            if selected_organization_id == "-1"
            else Organization.objects.get(id=selected_organization_id).short_name
        )
        response["Content-Disposition"] = (
            f'attachment; filename="Template_for_import_SushiCredentials_{org_suffix}.xlsx"'
        )
        return response

    @action(
        detail=True,
        methods=["get"],
        url_path="data",
        serializer_class=SushiCredentialsDataSerializer,
    )
    def data(self, request, pk):
        """Display data for given set of credentials"""
        credentials = get_object_or_404(self.get_queryset(), pk=pk)

        current_time = timezone.now()
        start_year = (
            credentials.fetchintention_set.aggregate(min_start=Min("start_date"))["min_start"]
            or current_time
        ).year - 1
        end_year = current_time.year

        report_types_and_broken = [
            (e.counter_report, e.is_broken())
            for e in credentials.counterreportstocredentials_set.all().select_related(
                "counter_report", "counter_report__report_type"
            )
        ]
        report_types = [e[0] for e in report_types_and_broken]

        data_matrix = ImportBatch.objects.data_matrix(
            organizations=[credentials.organization],
            platforms=[credentials.platform],
            report_types=[e.report_type for e in report_types],
        )
        data_matrix_map = {
            (e.report_type_id, e.date.year, e.date.month): e for e in data_matrix if e.date
        }

        result = {}
        # initialize output matrix
        for year in range(start_year, end_year + 1):
            year_result = {"year": year}
            for i in range(1, 13):
                year_result[f"{i:02d}"] = {}
                for crt, broken in report_types_and_broken:
                    if entry := data_matrix_map.get((crt.report_type.pk, year, i)):
                        status = "success" if bool(entry.record_count) else "no_data"
                        can_harvest = False
                    else:
                        status = "untried"
                        can_harvest = True

                    year_result[f"{i:02d}"][crt.code] = {
                        "status": status,
                        "planned": False,
                        "broken": broken,
                        "can_harvest": can_harvest and not broken,
                        "counter_report": {
                            "id": crt.pk,
                            "name": crt.name,
                            "code": crt.code,
                            "report_type": crt.report_type_id,
                        },
                    }
            result[year] = year_result

        # update planned
        for intention in credentials.fetchintention_set.filter(
            counter_report__in=report_types, when_processed__isnull=True, duplicate_of=None
        ).select_related("counter_report"):
            start = intention.start_date
            end = intention.end_date
            report_type = intention.counter_report.code

            # iterate through months
            while start <= end:
                if start.year in result:
                    result[start.year][f"{start.month:02d}"][report_type]["planned"] = True
                start += relativedelta(months=1)

        # iterate through attempts
        for attempt in credentials.attempts.filter(counter_report__in=report_types).select_related(
            "counter_report"
        ):
            start = attempt.start_date
            end = attempt.end_date
            report_type = attempt.counter_report.code
            status = attempt.status

            # iterate through months
            while start <= end:
                if start.year in result:
                    before = result[start.year][f"{start.month:02d}"][report_type]["status"]
                    if status in AttemptStatus.errors() and before in ["untried"]:
                        # untried => failed
                        result[start.year][f"{start.month:02d}"][report_type]["status"] = "failed"
                    elif attempt.partial_data and before in ["untried", "failed", "no_data"]:
                        # untried, failed, no_data => partial_data
                        result[start.year][f"{start.month:02d}"][report_type]["status"] = (
                            "partial_data"
                        )
                    elif status == AttemptStatus.NO_DATA and before in ["untried", "failed"]:
                        # failed, untried => no_data
                        result[start.year][f"{start.month:02d}"][report_type]["status"] = "no_data"
                    elif status == AttemptStatus.SUCCESS and before in [
                        "untried",
                        "failed",
                        "no_data",
                        "partial_data",
                    ]:
                        # failed, untried, no_data, partial_data => success
                        result[start.year][f"{start.month:02d}"][report_type]["status"] = "success"
                start += relativedelta(months=1)

        # reformat for serializer (dict => list)
        reformatted = list(result.values())
        for year_result in reformatted:
            for i in range(1, 13):
                key = f"{i:02d}"
                year_result[key] = sorted(
                    year_result[key].values(), key=lambda x: x["counter_report"]["id"]
                )

        serializer = SushiCredentialsDataSerializer(data=reformatted, many=True)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def count(self, request):
        """
        Just simple count of SushiCredentials
        """
        user_organizations = self.request.user.accessible_organizations()
        count = SushiCredentials.objects.filter(organization__in=user_organizations).count()
        broken = SushiCredentials.objects.filter(
            organization__in=user_organizations, broken__isnull=False
        ).count()
        broken_reports = CounterReportsToCredentials.objects.filter(
            credentials__organization__in=user_organizations, broken__isnull=False
        ).count()
        return Response({"count": count, "broken": broken, "broken_reports": broken_reports})

    @action(detail=False, methods=["get"], url_name="month-overview", url_path="month-overview")
    def month_overview(self, request):
        month = request.query_params.get("month")
        if not month:
            return Response(
                {"error": 'Missing "month" URL param'}, status=status.HTTP_400_BAD_REQUEST
            )

        month_date = parse_date_fuzzy(month)
        start = month_start(month_date)
        end = month_end(month_date)
        credentials = self.get_queryset()
        enabled_attr = (
            {"credentials__enabled": True} if "disabled" not in request.query_params else {}
        )
        query = (
            FetchIntention.objects.filter(
                start_date__lte=start,
                end_date__gte=end,
                credentials__in=credentials,
                counter_report=F("credentials__counter_reports"),
                duplicate_of__isnull=True,  # ignore duplicates
                **enabled_attr,
            )
            .order_by(
                "credentials_id",
                "counter_report_id",
                Cast("attempt__import_batch_id", BooleanField()).desc(
                    nulls_last=True
                ),  # no import_batch => last
                F("attempt__timestamp").desc(nulls_last=True),  # no attempt => last
            )
            .distinct("credentials_id", "counter_report_id")
            .select_related("credentials", "counter_report", "attempt", "attempt__counter_report")
        )
        records = MonthOverviewSerializer(query, many=True).data
        return Response(records)

    @action(
        detail=False,
        methods=["post"],
        url_path="switch-to-platforms-report-types",
        serializer_class=SwitchToPlatformsReportTypesSerializer,
    )
    def switch_to_platforms_report_types(self, request):
        serializer = SwitchToPlatformsReportTypesSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        credentials_ids = [e["credentials_id"] for e in serializer.validated_data]

        with transaction.atomic():
            credentials = self.get_queryset().filter(pk__in=credentials_ids)
            updated_count = credentials.filter(use_counter_reports_from_platform=False).update(
                use_counter_reports_from_platform=True
            )
            matched_count = credentials.count()

            credentials.update_report_types_based_on_platform()

        return Response(
            {
                "matched": matched_count,
                "updated": updated_count,
                "unmatched": len(set(credentials_ids)) - matched_count,
            }
        )


class CounterReportTypeViewSet(ReadOnlyModelViewSet):
    serializer_class = CounterReportTypeSerializer
    queryset = CounterReportType.objects.all()
