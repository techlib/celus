import json
import logging
from collections import Counter
from time import monotonic
from typing import Tuple

from core.exceptions import BadRequestException
from core.filters import PkMultiValueFilterBackend
from core.logic.bins import bin_hits
from core.logic.dates import date_filter_from_params, month_end
from core.logic.type_conversion import to_bool
from core.logic.util import text_hash
from core.models import DataSource
from core.permissions import SuperuserOrAdminPermission
from core.tasks import async_mail_customer_care_admins
from dal import autocomplete
from django.conf import settings
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.cache import cache
from django.db import connection, transaction
from django.db.models import Count, Exists, Max, Min, OuterRef, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponseBadRequest
from django.urls import reverse
from django.utils.translation import gettext as _
from logs.logic.interest.structure import get_interest_metrics_implying_availability
from logs.logic.queries import replace_report_type_with_materialized
from logs.models import (
    AccessLog,
    DimensionText,
    InterestConfig,
    Metric,
    OrganizationPlatform,
    ReportType,
)
from pycountry import subdivisions
from recache.util import recache_queryset
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet
from sushi.models import SushiCredentials
from sushi.tasks import send_grouped_harvesting_report_task, send_harvesting_report_task
from tags.models import Tag

from organizations.logic.queries import organization_filter_from_org_id
from organizations.tasks import erms_sync_organizations_task

from .models import COUNTRIES, Organization, UserOrganization
from .serializers import (
    GroupedHarvestReportSerializer,
    HarvestReportSerializer,
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
                send_harvest_reports=Exists(
                    UserOrganization.objects.filter(
                        organization=OuterRef("pk"),
                        user=self.request.user,
                        is_admin=True,  # only admins can receive reports
                        send_harvest_reports=True,
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

    @action(
        detail=True,
        methods=["post"],
        url_path="harvest-reports",
        serializer_class=HarvestReportSerializer,
    )
    def harvest_reports(self, request, pk):
        serializer = HarvestReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = get_object_or_404(request.user.admin_organizations(), pk=pk)
        enabled = serializer.validated_data["enabled"]

        if enabled:
            # make sure that UserOrganization organization exists for
            # super users and consortial admins
            _, created = UserOrganization.objects.get_or_create(
                user=request.user,
                organization=organization,
                defaults={"is_admin": True, "send_harvest_reports": enabled},
            )
            if created:
                return Response()

        UserOrganization.objects.filter(user=request.user, organization__pk=pk).update(
            send_harvest_reports=enabled
        )
        return Response()

    @action(
        detail=False,
        methods=["post"],
        url_path="grouped-harvest-reports",
        serializer_class=GroupedHarvestReportSerializer,
    )
    def grouped_harvest_reports(self, request):
        serializer = GroupedHarvestReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enabled = serializer.validated_data["enabled"]

        request.user.send_grouped_harvest_reports = enabled
        request.user.save()

        return Response()

    @action(detail=True, methods=["post"], url_path="send-harvest-report")
    def send_harvest_report(self, request, pk):
        organization = get_object_or_404(request.user.admin_organizations(), pk=pk)
        send_harvesting_report_task.delay(request.user.pk, organization.pk)
        return Response()

    @action(detail=False, methods=["post"], url_path="send-grouped-harvest-report")
    def send_grouped_harvest_report(self, request):
        send_grouped_harvesting_report_task.delay(request.user.pk)
        return Response()

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

For more info see Django admin: {
                request.build_absolute_uri(
                    reverse("admin:organizations_organization_change", args=[org.id])
                )
            }.
""",
        )
        return Response(OrganizationSerializer(org).data, status=status.HTTP_201_CREATED)

    def _overlap_accesslog_filters(self, request, pk) -> Tuple[str, dict, dict, dict]:
        """
        Returns

        * a string with SQL WHERE part,
        * a dictionary with parameters for the WHERE part,
        * a dictionary with positive filters for the AccessLog query as used by Django ORM,
        * a dictionary with negative filters for the AccessLog query as used by Django ORM.

        All are related to accesslogs filters applied to the request and used for overlap analysis.
        """
        org_filter = organization_filter_from_org_id(pk, request.user, prefix="")
        logger.debug("Org filter: %s", org_filter)
        date_filter = date_filter_from_params(request.GET)
        interest_rt = ReportType.objects.get_interest_rt()
        metric_ids = [m.pk for m in get_interest_metrics_implying_availability()]

        where_parts = ["report_type_id = %(rt_id)s", "metric_id IN %(metric_ids)s"]
        where_params = {"rt_id": interest_rt.pk, "metric_ids": tuple(metric_ids)}
        if "date__gte" in date_filter:
            where_parts.append("date >= %(date__gte)s")
            where_params.update(date_filter)
        if "date__lte" in date_filter:
            where_parts.append("date <= %(date__lte)s")
            where_params.update(date_filter)
        if org_filter:
            where_parts.append("organization_id = %(org_id)s")
            where_params["org_id"] = org_filter["organization__pk"]
            org = get_object_or_404(Organization.objects.filter(id=org_filter["organization__pk"]))
            ic = org.get_interest_config()
        else:
            ic = InterestConfig.objects.default()
        # handle interest config
        ic_filters = {}
        ic_neg_filters = {}
        for negated, fltrs in zip((False, True), ic.get_interest_filters(), strict=True):
            for fltr, values in fltrs.items():
                if negated:
                    ic_neg_filters[fltr] = values
                else:
                    ic_filters[fltr] = values
                dim, mod = fltr.split("__")
                if mod == "in":
                    if negated:
                        where_parts.append(f"{dim} NOT IN %(dim_values_{dim})s")
                    else:
                        where_parts.append(f"{dim} IN %(dim_values_{dim})s")
                    where_params[f"dim_values_{dim}"] = tuple(values)
                else:
                    raise ValueError(f"Invalid filter: {fltr}")

        if where_part := " AND ".join(where_parts):
            where_part = "WHERE " + where_part

        return (
            where_part,
            where_params,
            {
                "report_type": interest_rt,
                "metric_id__in": metric_ids,
                **org_filter,
                **date_filter,
                **ic_filters,
            },
            ic_neg_filters,
        )

    @action(detail=True, url_path="platform-overlap")
    def platform_overlap(self, request, pk):
        """
        API that returns a specific reply for platform-platform overlap analysis
        """
        where_sql, where_params, *_unused = self._overlap_accesslog_filters(request, pk)

        query = f"""
          SELECT A."platform_id",
                 B."platform_id",
                 COUNT(DISTINCT A."title_id") AS "count",
                 SUM(value) AS sum
          FROM
              (SELECT organization_id, platform_id, target_id as title_id, SUM(value) AS value
               FROM logs_accesslog {where_sql}
               GROUP BY organization_id, platform_id, target_id
               ) AS A
            INNER JOIN
              (SELECT DISTINCT organization_id, platform_id, target_id as title_id
               FROM logs_accesslog {where_sql}) AS B
            ON (A."title_id" = B."title_id" AND A."organization_id" = B."organization_id")
          GROUP BY A."platform_id", B."platform_id";"""
        logger.debug("Overlap raw query: %s", query)

        # neither recache nor cachalot do support raw queries, so we cache it using django caching
        cache_key = "platform-overlap-" + text_hash(query % where_params)
        if not (result := cache.get(cache_key, None)):
            with connection.cursor() as cursor:
                start = monotonic()
                cursor.execute(query, where_params)
                result = [
                    {"platform1": p1, "platform2": p2, "overlap": overlap, "interest": interest}
                    for p1, p2, overlap, interest in cursor.fetchall()
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
        by a hand-crafted raw SQL query.
        """
        where_sql, where_params, accesslog_filters, accesslog_neg_filters = (
            self._overlap_accesslog_filters(request, pk)
        )

        query = f"""
        SELECT X.platform_id,
               COALESCE(SUM(X.value), 0) as sum,
               COUNT(DISTINCT X.title_id) as count
        FROM (
        SELECT A.platform_id,
               A.title_id,
               MIN(A.value) AS value -- for each platform and title, take only one value -
               -- all are the same anyway, so we use min
               -- this prevents double counting when a title is on multiple other platforms
        FROM (SELECT organization_id,
                     platform_id,
                     target_id as title_id,
                     SUM(value) AS value
              FROM logs_accesslog {where_sql}
              GROUP BY organization_id, platform_id, target_id) AS A
                 INNER JOIN (SELECT DISTINCT organization_id,
                                             platform_id,
                                             target_id as title_id
                             FROM logs_accesslog {where_sql}) AS B
                            ON (A."title_id" = B."title_id" AND
                                A."organization_id" = B."organization_id" AND
                                A."platform_id" != B."platform_id")
        GROUP BY A."platform_id", A.title_id) AS X
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
        replace_report_type_with_materialized({**accesslog_filters, **accesslog_neg_filters})
        total_overlap_interests = (
            AccessLog.objects.filter(**accesslog_filters)
            .exclude(**accesslog_neg_filters)
            .values("platform")
            .annotate(interest=Coalesce(Sum("value"), 0))
        )
        total_overlap_interests = recache_queryset(
            total_overlap_interests, origin="APO-total-interest"
        )
        pk_to_total_interest = {rec["platform"]: rec["interest"] for rec in total_overlap_interests}

        org_filter = organization_filter_from_org_id(pk, request.user, prefix="")
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

    @action(detail=True, url_path="titles-on-multiple-platforms")
    def titles_on_multiple_platforms(self, request, pk):
        # _accesslog_neg_filters is not used here because it contains only interest-specific
        # filters which are not relevant for the titles-on-multiple-platforms query
        where_sql, where_params, accesslog_filters, _accesslog_neg_filters = (
            self._overlap_accesslog_filters(request, pk)
        )

        # pagination and ordering parameters
        try:
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 25))
        except (ValueError, TypeError):
            raise BadRequestException(
                "Page and page_size parameters must be valid integers"
            ) from None
        if page < 1:
            raise BadRequestException("Page number must be at least 1")
        if page_size < 1:
            raise BadRequestException("Page size must be at least 1")
        where_params["limit"] = page_size
        where_params["offset"] = (page - 1) * page_size
        order_by = request.query_params.get("order_by", "total_interest")
        if order_by in ("name", "isbn", "issn", "eissn", "doi", "pub_type"):
            order_by = f"t.{order_by}"
        elif order_by in ("total_interest", "platform_count"):
            pass
        else:
            raise BadRequestException(f"Invalid order_by value: {order_by}")
        desc = to_bool(request.query_params.get("desc", "true"))
        desc_chunk = "DESC" if desc else "ASC"

        # title filters
        title_where_parts = []

        if q := request.query_params.get("q"):
            full_text_attrs = ("name", "isbn", "issn", "eissn", "doi")
            for i, p in enumerate(q.split()):
                title_where_parts.append(
                    "("
                    + " OR ".join(f"t.{attr} ILIKE %(q{i:03})s" for attr in full_text_attrs)
                    + ")"
                )
                where_params[f"q{i:03}"] = f"%{p}%"
        if pub_type := request.query_params.get("pub_type"):
            title_where_parts.append("t.pub_type = %(pub_type)s")
            where_params["pub_type"] = pub_type
        if tags := request.query_params.get("tags", "").strip():
            tag_ids = [int(tag_id) for tag_id in tags.split(",")]
            # clean the tag_ids to only those that are accessible by the user
            if tag_ids := tuple(
                Tag.objects.user_accessible_tags(self.request.user)
                .filter(pk__in=tag_ids)
                .values_list("pk", flat=True)
            ):
                title_where_parts.append(
                    "t.id IN "
                    "(SELECT DISTINCT target_id FROM tags_titletag WHERE tag_id IN %(tags)s)"
                )
                where_params["tags"] = tag_ids
            else:
                # no tags made it through the filter, so we want to return an empty result
                # (for some reason, `IN ()` does not work in Postgres)
                title_where_parts.append("FALSE")

        title_where_sql = ""
        if title_where_parts:
            title_where_sql = "WHERE " + " AND ".join(title_where_parts)

        query = f"""
        SELECT target_id, total_interest, platform_count, platform_interest, _count,
               t.name, t.pub_type, t.isbn, t.issn, t.eissn, t.doi, t.proprietary_ids
        FROM(
            SELECT target_id,
                   COALESCE(SUM(X."value"), 0)               AS "total_interest",
                   COUNT(DISTINCT X."platform_id")           AS "platform_count",
                   json_object_agg(X."platform_id", X.value) AS platform_interest,
                   COUNT(*) OVER ()                          AS "_count"
            FROM (
                SELECT target_id, platform_id, SUM(value) as value
                    FROM logs_accesslog {where_sql}
                    GROUP BY target_id, platform_id
                ) AS X
            GROUP BY target_id
            HAVING COUNT(X."platform_id") > 1
            ) AS Y
        JOIN publications_title t ON t.id = Y.target_id
        {title_where_sql}
        ORDER BY {order_by} {desc_chunk}
        LIMIT %(limit)s OFFSET %(offset)s;
        """
        logger.debug("Titles on multiple platforms raw query: %s", query)
        total_count = 0
        result = []
        with connection.cursor() as cursor:
            cursor.execute(query, where_params)
            for (
                target_id,
                total_interest,
                platform_count,
                platform_interest,
                _count,
                name,
                pub_type,
                isbn,
                issn,
                eissn,
                doi,
                proprietary_ids,
            ) in cursor.fetchall():
                total_count = _count

                result.append(
                    {
                        "pk": target_id,
                        "name": name,
                        "issn": issn,
                        "isbn": isbn,
                        "eissn": eissn,
                        "doi": doi,
                        "pub_type": pub_type,
                        "proprietary_ids": proprietary_ids,
                        "total_interest": int(total_interest),
                        "platform_count": platform_count,
                        "interests": platform_interest,
                    }
                )

        # add YOP information from the TR
        yop_excluded_metrics = [
            "No_License",
            "Limit_Exceeded",
            "Total_Item_Investigations",
            "Unique_Item_Investigations",
        ]
        allowed_access_types = ["Controlled"]
        try:
            tr = ReportType.objects.get(short_name="TR")
        except ReportType.DoesNotExist:
            # if TR report is not present, we can't add YOPs
            return Response({"count": total_count, "results": result})

        dim_ref = tr.dim_name_to_dim_attr("YOP")
        title_ids = {r["pk"] for r in result}
        excluded_metrics = Metric.objects.filter(short_name__in=yop_excluded_metrics)
        # we want to limit the access types to only "Controlled", OA will be available regardless
        # of the subscription the organization has
        access_type_dim_ref = tr.dim_name_to_dim_attr("Access_Type")
        access_type_dim = tr.dimension_by_attr_name(access_type_dim_ref)
        access_type_ids = {
            dt.pk
            for dt in DimensionText.objects.filter(
                text__in=allowed_access_types, dimension=access_type_dim
            )
        }
        # add list of non-null YOPs for each title
        # we use the filters from the above `accesslog_filters` but we remove those which are
        # interest specific:
        # - `report_type`
        # - `metric_id__in`
        # - all explicit dimensions (those are for interest, not for TR)
        al_filters = {
            k: v
            for k, v in accesslog_filters.items()
            if k not in ("report_type", "metric_id__in") and not k.startswith("dim")
        }
        al_filters[f"{access_type_dim_ref}__in"] = access_type_ids
        qs = (
            AccessLog.objects.filter(
                target_id__in=title_ids,
                report_type_id=tr.pk,
                **{f"{dim_ref}__isnull": False},
                **al_filters,
            )
            .exclude(metric_id__in=excluded_metrics)
            .values("target_id", "platform_id")
            .annotate(yop_ids=ArrayAgg(dim_ref, distinct=True))
        )
        # the YOPs are just ids in DimensionText, we need to map them to actual values
        all_yop_ids = set()
        title_platform_ids_to_yop_ids = {}
        for rec in qs:
            all_yop_ids.update(rec["yop_ids"])
            title_platform_ids_to_yop_ids[(rec["target_id"], rec["platform_id"])] = rec["yop_ids"]
        remap = {
            rec["pk"]: rec["text"]
            for rec in DimensionText.objects.filter(pk__in=all_yop_ids).values("pk", "text")
        }
        for record in result:
            yops_rec = {}
            for platform_id in record["interests"].keys():
                platform_id = int(platform_id)
                yops = set()
                for yop_id in title_platform_ids_to_yop_ids.get((record["pk"], platform_id), []):
                    yop = remap[yop_id]
                    try:
                        yop = int(yop)
                    except ValueError:
                        # we are only interested in integer values which represent years
                        continue
                    if 1000 < yop < 3000:
                        # 0001 and 9999 are used as placeholders for unknown years or ahead of print
                        # to guard against other strange values, we only accept years between
                        # 1000 and 3000
                        yops.add(yop)
                if yops:
                    yops_rec[platform_id] = {"min": min(yops), "max": max(yops)}
            record["yops"] = yops_rec
        return Response({"count": total_count, "results": result})


class StartERMSSyncOrganizationsTask(APIView):
    permission_classes = [SuperuserOrAdminPermission]

    def post(self, request):
        task = erms_sync_organizations_task.delay()
        return Response({"id": task.id})


class CountryAutocompleteView(autocomplete.Select2ListView):
    def get_list(self):
        if not self.request.user.is_staff:
            return []

        return COUNTRIES


class StateAutocompleteView(autocomplete.Select2ListView):
    def get_list(self):
        if not self.request.user.is_staff:
            return []

        return [
            (e.code, f"({e.country_code}) {_(e.name)}")
            for e in subdivisions
            if e.type == "State" and self.forwarded.get("country") == e.country_code
        ]
