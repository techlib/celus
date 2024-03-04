import json
import logging
from collections import Counter
from time import monotonic

from core.filters import PkMultiValueFilterBackend
from core.logic.bins import bin_hits
from core.logic.dates import date_filter_from_params, month_end
from core.logic.util import text_hash
from core.models import DataSource
from core.permissions import SuperuserOrAdminPermission
from core.tasks import async_mail_customer_care_admins
from django.conf import settings
from django.core.cache import cache
from django.db import connection, transaction
from django.db.models import Count, Exists, Max, Min, OuterRef, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponseBadRequest
from django.urls import reverse
from logs.logic.queries import replace_report_type_with_materialized
from logs.models import AccessLog, OrganizationPlatform, ReportType
from recache.util import recache_queryset
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet
from sushi.models import SushiCredentials

from organizations.logic.queries import organization_filter_from_org_id
from organizations.tasks import erms_sync_organizations_task

from .models import Organization, UserOrganization
from .serializers import (
    OrganizationListSerializer,
    OrganizationSerializer,
    OrganizationSimpleSerializer,
)

logger = logging.getLogger(__name__)


class OrganizationViewSet(ReadOnlyModelViewSet):
    serializer_class = OrganizationListSerializer
    histogram_bins = [
        (0, 0),
        (1, 1),
        (2, 5),
        (6, 10),
        (11, 20),
        (21, 50),
        (51, 100),
        (101, 200),
        (201, 500),
        (501, 1000),
    ]
    queryset = Organization.objects.all()
    filter_backends = [PkMultiValueFilterBackend]

    def get_queryset(self):
        """
        Should return only organizations associated with the current user
        :return:
        """
        qs = super().get_queryset()
        qs = qs.filter(pk__in=self.request.user.accessible_organizations())
        return (
            qs.annotate(
                is_admin=Exists(
                    UserOrganization.objects.filter(
                        organization=OuterRef("pk"), user=self.request.user, is_admin=True
                    )
                ),
                is_member=Exists(
                    UserOrganization.objects.filter(
                        organization=OuterRef("pk"), user=self.request.user
                    )
                ),
            )
            .order_by("name")
            .prefetch_related("organizationaltname_set")
        )

    @action(detail=True, url_path="sushi-credentials-versions")
    def sushi_credentials_versions(self, request, pk):
        org_filter = organization_filter_from_org_id(pk, request.user)
        data = (
            SushiCredentials.objects.filter(**org_filter)
            .annotate(count=Count("pk"))
            .values("platform", "counter_version", "outside_consortium", "count")
            .filter(count__gt=0)
            .distinct()
        )
        result = {}
        for rec in data:
            if rec["platform"] not in result:
                result[rec["platform"]] = []
            result[rec["platform"]].append(
                {"version": rec["counter_version"], "outside_consortium": rec["outside_consortium"]}
            )
        for value in result.values():
            value.sort(key=lambda x: x["version"])
        return Response(result)

    @action(detail=True, url_path="year-interest")
    def year_interest(self, request, pk):
        org_filter = organization_filter_from_org_id(pk, request.user)
        interest_rt = ReportType.objects.get_interest_rt()
        result = []
        for rec in (
            AccessLog.objects.filter(report_type=interest_rt, **org_filter)
            .values("date__year")
            .distinct()
            .annotate(interest_sum=Sum("value"))
            .order_by("date__year")
        ):
            # this is here purely to facilitate renaming of the keys
            result.append({"year": rec["date__year"], "interest": rec["interest_sum"]})
        return Response(result)

    @action(detail=True, url_path="interest")
    def interest(self, request, pk):
        org_filter = organization_filter_from_org_id(pk, request.user)
        date_filter = date_filter_from_params(request.GET)
        interest_rt = ReportType.objects.get_interest_rt()
        accesslog_filter_params = {"report_type": interest_rt, **org_filter, **date_filter}
        replace_report_type_with_materialized(accesslog_filter_params)
        # The following is a more natural query for this data, but because aggregate
        # returns a dict in Django, it would not be possible to recache the result
        # (we need a queryset for this).
        #
        # data = AccessLog.objects.filter(**accesslog_filter_params).aggregate(
        #     interest_sum=Sum('value'), min_date=Min('date'), max_date=Max('date')
        # )
        #
        # This is why we use the following hack where we annotate a static value
        # which leads to the same SQL query, but creates a queryset which can be recached.
        data = recache_queryset(
            AccessLog.objects.filter(**accesslog_filter_params)
            .annotate(foo=Value(42))
            .values("foo")
            .annotate(interest_sum=Sum("value"), min_date=Min("date"), max_date=Max("date")),
            origin="organization-interest",
        )
        data = data[0]
        del data["foo"]  # residual static value
        if data.get("max_date"):
            # the date might be None and then we do not want to do the math ;)
            data["max_date"] = month_end(data["max_date"])
            data["days"] = (data["max_date"] - data["min_date"]).days + 1
        else:
            data["days"] = 0
        return Response(data)

    @action(detail=True, url_path="title-interest-histogram")
    def title_interest_histogram(self, request, pk):
        org_filter = organization_filter_from_org_id(pk, request.user)
        date_filter = date_filter_from_params(request.GET)
        interest_rt = ReportType.objects.get_interest_rt()
        counter = Counter()
        query = (
            AccessLog.objects.filter(report_type=interest_rt, **org_filter, **date_filter)
            .values("target")
            .annotate(interest_sum=Coalesce(Sum("value"), 0))
            .values("interest_sum")
        )
        for rec in query:
            counter[rec["interest_sum"]] += 1
        # here we bin it according to self.histogram_bins
        bin_counter = bin_hits(counter, histogram_bins=self.histogram_bins)

        # objects to return
        def name(a, b):
            if a == b:
                return str(a)
            return f"{a}-{b}"

        data = [
            {"count": count, "start": start, "end": end, "name": name(start, end)}
            for (start, end), count in sorted(bin_counter.items())
        ]
        return Response(data)

    @action(detail=False, methods=["post"], url_path="create-user-default")
    @transaction.atomic()
    def create_user_default(self, request):
        """
        Lets a user create an organization if account creation is allowed and this user does
        not have an organization yet.
        """
        if not settings.ALLOW_USER_REGISTRATION:
            return HttpResponseBadRequest(
                json.dumps({"error": "Organization creation is not allowed"}),
                content_type="application/json",
            )
        organization_count = request.user.organizations.count()
        if organization_count > 0:
            return HttpResponseBadRequest(
                json.dumps({"error": "User is allowed to create only one organization"}),
                content_type="application/json",
            )
        serializer = OrganizationSimpleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        valid_data = serializer.validated_data
        slugified_name = DataSource.create_default_short_name(request.user, valid_data["name"])
        if DataSource.objects.filter(short_name=slugified_name).exists():
            conflicting_name = (
                DataSource.objects.filter(short_name=slugified_name).first().short_name
            )
            return HttpResponseBadRequest(
                json.dumps(
                    {
                        "error": f"'{valid_data['name']}' and existing '{conflicting_name}'"
                        f" can't be used together because they both map to '{slugified_name}'"
                    }
                ),
                content_type="application/json",
            )

        org = serializer.create(valid_data)
        # update all language mutations
        # so the organization name is properly shown even when langage changes
        for lang in settings.MODELTRANSLATION_LANGUAGES:
            setattr(org, f"name_{lang}", valid_data["name"])
            setattr(org, f"short_name_{lang}", valid_data["name"][:100])

        data_source = DataSource.objects.create(
            organization=org, type=DataSource.TYPE_ORGANIZATION, short_name=slugified_name
        )
        # we add the just created data source as source for the organization itself
        # it looks strange, but it is a usable way how to say that this is a user-created
        # organization
        org.source = data_source
        org.internal_id = slugified_name
        org.save()
        # associate the user with this organization as admin
        UserOrganization.objects.create(
            user=request.user, organization=org, is_admin=True, source=data_source
        )
        async_mail_customer_care_admins.delay(
            f"New organization created - {org.name}",
            f"""\
A new organization was created by the user.

User name: {request.user.first_name} {request.user.last_name}
User email: {request.user.email}
Organization name: {org.name}
Organization id: {org.id}

For more info see Django admin: {request.build_absolute_uri(
    reverse('admin:organizations_organization_change', args=[org.id])
    )}.
""",
        )
        return Response(OrganizationSerializer(org).data, status=status.HTTP_201_CREATED)

    @action(detail=True, url_path="platform-overlap")
    def platform_overlap(self, request, pk):
        """
        API that returns a specific reply for platform-platform overlap analysis
        """
        org_filter = organization_filter_from_org_id(pk, request.user, prefix=None)
        date_filter = date_filter_from_params(request.GET)
        main_where_parts = []
        sub_where_parts = []
        where_params = {}
        if "date__gte" in date_filter:
            sub_where_parts.append("date >= %(date__gte)s")
            where_params.update(date_filter)
        if "date__lte" in date_filter:
            sub_where_parts.append("date <= %(date__lte)s")
            where_params.update(date_filter)
        if org_filter:
            main_where_parts.append(
                "A.organization_id = %(org_id)s AND B.organization_id = %(org_id)s"
            )
            where_params["org_id"] = org_filter["pk"]

        main_where_part = " AND ".join(main_where_parts)
        if main_where_part:
            main_where_part = "WHERE " + main_where_part

        sub_where_part = " AND ".join(sub_where_parts)
        if sub_where_part:
            sub_where_part = "WHERE " + sub_where_part

        query = f"""
          SELECT A."platform_id",
                 B."platform_id",
                 COUNT(DISTINCT A."title_id") AS "count"
          FROM
              (SELECT DISTINCT organization_id, platform_id, title_id FROM
               publications_platformtitle {sub_where_part}) AS A
            INNER JOIN
              (SELECT DISTINCT organization_id, platform_id, title_id FROM
               publications_platformtitle {sub_where_part}) AS B
            ON (A."title_id" = B."title_id" AND A."organization_id" = B."organization_id")
            {main_where_part}
          GROUP BY A."platform_id", B."platform_id";"""
        logger.debug("Overlap raw query: %s", query)

        # neither recache nor cachalot do support raw queries, so we cache it using django caching
        cache_key = "platform-overlap-" + text_hash(query % where_params)
        if not (result := cache.get(cache_key, None)):
            with connection.cursor() as cursor:
                start = monotonic()
                cursor.execute(query, where_params)
                result = [
                    {"platform1": p1, "platform2": p2, "overlap": overlap}
                    for p1, p2, overlap in cursor.fetchall()
                ]
                if monotonic() - start > 2:
                    # only cache results that take more than 2 seconds to compute
                    # we also use a short time for caching to avoid stale results
                    # (the purpose of the cache is just to allow quick return to the corresponding
                    #  frontend page after the user tried some other overlap related page)
                    cache.set(cache_key, result, timeout=5 * 60)

        return Response(result)

    @action(detail=True, url_path="all-platforms-overlap")
    def all_platforms_overlap(self, request, pk):
        """
        API that returns an overlap of each platform with all the other platforms together.

        This view uses similar approach to the previous one - most of the calculation is done
        by a hand crafter raw SQL query.

        Compared to the previous version this one fixes an error where overlap was sometimes
        reported in interest even thouth the overlapping titles were for different organizations.
        It is also significantly faster. In my tests on copy of K1 db it took 18 seconds
        compared to 76 seconds for the previous version.
        """
        org_filter = organization_filter_from_org_id(pk, request.user, prefix="")
        date_filter = date_filter_from_params(request.GET)
        interest_rt = ReportType.objects.get_interest_rt()
        main_where_parts = []
        sub_where_parts = []
        join_parts = ["report_type_id = %(rt_id)s"]
        where_params = {"rt_id": interest_rt.pk}
        if "date__gte" in date_filter:
            sub_where_parts.append("date >= %(date__gte)s")
            join_parts.append("date >= %(date__gte)s")
            where_params.update(date_filter)
        if "date__lte" in date_filter:
            sub_where_parts.append("date <= %(date__lte)s")
            join_parts.append("date <= %(date__lte)s")
            where_params.update(date_filter)
        if org_filter:
            main_where_parts.append(
                "A.organization_id = %(org_id)s AND B.organization_id = %(org_id)s"
            )
            sub_where_parts.append("organization_id = %(org_id)s")
            join_parts.append("organization_id = %(org_id)s")
            where_params["org_id"] = org_filter["organization__pk"]

        if main_where_part := " AND ".join(main_where_parts):
            main_where_part = "WHERE " + main_where_part

        if sub_where_part := " AND ".join(sub_where_parts):
            sub_where_part = "WHERE " + sub_where_part

        if join_part := " AND ".join(join_parts):
            join_part = "AND " + join_part

        # left outer join below is used to correctly count all the titles, not only
        # those with interest
        query = f"""
        SELECT X.platform_id, COALESCE(SUM(al.value), 0), COUNT(DISTINCT X.title_id)
            FROM (
                SELECT A."platform_id", A."title_id"
                FROM (
                    SELECT DISTINCT organization_id,
                           platform_id,
                           title_id
                      FROM publications_platformtitle {sub_where_part}
                    ) AS A
                    INNER JOIN (
                        SELECT DISTINCT organization_id,
                               platform_id,
                               title_id
                          FROM publications_platformtitle {sub_where_part}
                       ) AS B
                    ON (A."title_id" = B."title_id"
                        AND A."organization_id" = B."organization_id"
                        AND A."platform_id" != B."platform_id")
                    {main_where_part}
                    GROUP BY A."platform_id", A.title_id
                ) AS X
        LEFT OUTER JOIN logs_accesslog al
            ON al.platform_id = X.platform_id
            {join_part}
            AND target_id = X.title_id
        GROUP BY X.platform_id;
        """
        start = monotonic()
        # neither recache nor cachalot do support raw queries, so we cache it using django caching
        cache_key = "all-platforms-overlap-" + text_hash(query % where_params)
        if not (pid_to_counts := cache.get(cache_key, {})):
            with connection.cursor() as cursor:
                cursor.execute(query, where_params)
                for p, interest, title_count in cursor.fetchall():
                    pid_to_counts[p] = (interest, title_count)
                if monotonic() - start > 2:
                    # only cache results that take more than 2 seconds to compute
                    # we also use a short time for caching to avoid stale results
                    # (the purpose of the cache is just to allow quick return to the corresponding
                    #  frontend page after the user tried some other overlap related page)
                    cache.set(cache_key, pid_to_counts, timeout=5 * 60)

        # overall interest
        accesslog_filter = {"report_type": interest_rt, **org_filter, **date_filter}
        replace_report_type_with_materialized(accesslog_filter)
        total_overlap_interests = (
            AccessLog.objects.filter(**accesslog_filter)
            .values("platform")
            .annotate(interest=Coalesce(Sum("value"), 0))
        )
        total_overlap_interests = recache_queryset(
            total_overlap_interests, origin="APO-total-interest"
        )
        pk_to_total_interest = {rec["platform"]: rec["interest"] for rec in total_overlap_interests}

        org_pl_qs = OrganizationPlatform.objects.filter(**org_filter)
        result = [
            {
                "platform": pl_id,
                "overlap": pid_to_counts.get(pl_id, (0, 0))[1],
                "overlap_interest": pid_to_counts.get(pl_id, (0, 0))[0],
                "total_interest": pk_to_total_interest.get(pl_id, 0),
            }
            for pl_id in org_pl_qs.values_list("platform_id", flat=True).distinct()
        ]
        return Response(result)


class StartERMSSyncOrganizationsTask(APIView):
    permission_classes = [SuperuserOrAdminPermission]

    def post(self, request):
        task = erms_sync_organizations_task.delay()
        return Response({"id": task.id})
