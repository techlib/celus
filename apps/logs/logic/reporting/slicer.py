import datetime
import operator
from collections import OrderedDict
from enum import Enum
from functools import reduce
from typing import Iterable, List, Optional, Set, Tuple, Type

from core.logic.dates import date_range_from_params, month_end, parse_month
from core.logic.serialization import parse_b64json
from core.logic.type_conversion import to_bool
from django.conf import settings
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.exceptions import EmptyResultSet
from django.db.models import (
    Case,
    CharField,
    DateField,
    Exists,
    F,
    FilteredRelation,
    ForeignKey,
    IntegerField,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Concat, NullIf
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from hcube.api.models.aggregation import Sum as HSum
from organizations.logic.queries import extend_query_filter
from organizations.models import Organization
from tags.models import Tag, TagClass

from logs.cubes import AccessLogCube, ch_backend
from logs.logic.data_coverage import DataCoverageExtractor
from logs.logic.queries import find_best_materialized_view, logger
from logs.logic.reporting.filters import (
    CLICKHOUSE_ID_COUNT_LIMIT,
    ClickhouseIncompatibleFilter,
    DateDimensionFilter,
    DimensionFilter,
    ExplicitDimensionFilter,
    ForeignKeyDimensionFilter,
    TagClassDimensionFilter,
    TagDimensionFilter,
)
from logs.models import AccessLog, Dimension, DimensionText, ImportBatch, ReportType


class FlexibleDataSlicer:
    implicit_dims = ["date", "platform", "metric", "organization", "target", "report_type"]
    COL_BASE = "base"
    COL_COMPARED = "compared"
    COL_DIFF = "diff"
    COL_REL_DIFF = "reldiff"
    COL_TOTAL = "_total"
    MAXIMUM_POSSIBLE_PARTS = 1000

    TREND_MODE_COLS = (COL_BASE, COL_COMPARED, COL_DIFF, COL_REL_DIFF)

    @classmethod
    def get_pk_key(cls, index: int) -> str:
        """
        Get the primary key field name for a given dimension index.
        Always returns 'pk' for index 0, 'pk2' for index 1, etc.
        """
        return "pk" if index == 0 else f"pk{index + 1}"

    def __init__(
        self,
        primary_dimensions,
        *,
        tag_roll_up=False,
        include_all_zero_rows=False,
        include_row_totals=False,
        include_col_totals=False,
        trend_mode=False,
        base_subset_filters: Optional[List[DimensionFilter]] = None,
        compared_subset_filters: Optional[List[DimensionFilter]] = None,
        merge_report_types=False,
        use_clickhouse=None,
    ):
        """
        :param primary_dimensions: The dimension(s) that will be used to group the results into
            rows. Can be a single dimension string or a list of dimension strings for multiindex
            support.
        :param tag_roll_up: When active, the results for individual primary objects will be summed
            up for individual tags assigned to the primary objects. `tag_filter` and `tag_class`
            help narrow down the tags that will be included in the results.
        :param include_all_zero_rows: Changes the way the query is constructed to include all
            objects from the primary dimension, even if they have no data. In some cases,
            this does not work with ClickHouse, so it should be avoided as much as possible.
        :param trend_mode: Instead of grouping by a dimension, values for two explicitly specified
            subsets of data will be compared - `base_subset` and `compared_subset`
        :param base_subset_filters: list of filters applied to the base subset in trend mode
        :param compared_subset_filters: list of filters applied to the compared subset in trend
        :param merge_report_types: if True, the report types will be merged into a single one
            with the same dimensions and filters
        :param use_clickhouse: whether to use ClickHouse for queries where it is supported
        """
        self.use_clickhouse = (
            settings.CLICKHOUSE_QUERY_ACTIVE if use_clickhouse is None else use_clickhouse
        )
        # Handle both single dimension and list of dimensions for backward compatibility
        if isinstance(primary_dimensions, str):
            self.primary_dimensions = [primary_dimensions]
        else:
            self.primary_dimensions = list(primary_dimensions)
        # trend_mode
        self.trend_mode = trend_mode
        self.base_subset_filters = base_subset_filters or []
        self.compared_subset_filters = compared_subset_filters or []
        if self.trend_mode:
            if not (self.base_subset_filters and self.compared_subset_filters):
                raise ValueError(
                    "`base_subset_filters` and `compared_subset_filters` must be specified when "
                    "`trend_mode` is True"
                )
            if not all(
                isinstance(f, DateDimensionFilter)
                for f in self.base_subset_filters + self.compared_subset_filters
            ):
                raise ValueError(
                    "Only date filters are implemented for subsets in trend mode for now"
                )

        self.dimension_filters: List[DimensionFilter] = []
        self.group_by = []
        self.order_by = []
        self.split_by = []
        self._annotations = []
        self.organization_filter = None
        self.include_all_zero_rows = include_all_zero_rows
        self.include_row_totals = include_row_totals
        self.include_col_totals = include_col_totals
        self.merge_report_types = merge_report_types
        self.tag_roll_up = tag_roll_up
        self.tag_filter: Optional[Q] = None
        self.tag_class: Optional[int] = None
        # the following is only here for storage - we do not use it in the code, but
        # we need it for serialization
        self.show_untagged_remainder: bool = False
        # if True, the query is run against the model described by the primary dimension
        # for example Title and annotated with access log data
        # if False, the query is done against the access log model
        self._primary_dimension_query = False
        # if materialized report is used, we store a mapping between the used report type id
        # and the requested (original) report type id
        self._mat_reports_map = {}

    def config(self):
        return {
            "primary_dimensions": self.primary_dimensions,
            "filters": [fltr.config() for fltr in self.dimension_filters],
            "group_by": self.group_by,
            "order_by": self.order_by,
            "zero_rows": self.include_all_zero_rows,
            "row_totals": self.include_row_totals,
            "col_totals": self.include_col_totals,
            "split_by": self.split_by,
            "tag_roll_up": self.tag_roll_up,
            "tag_class": self.tag_class,
            "show_untagged_remainder": self.show_untagged_remainder,
            "trend_mode": self.trend_mode,
            "base_subset_filters": [fltr.config() for fltr in self.base_subset_filters],
            "compared_subset_filters": [fltr.config() for fltr in self.compared_subset_filters],
            "merge_report_types": self.merge_report_types,
        }

    def create_filters(
        self, ignore_dimensions=None, use_clickhouse=False, remainder=False
    ) -> Tuple[dict, list, list]:
        """
        Returns a dict with filters in the kwargs format and a list with Q-based filters.

        When `remainder` is True, the filters are created for the remainder calculation.
        This means that in tag_roll_up mode, the prefix related to titles, not tags.
        """
        if remainder and not self.tag_roll_up:
            raise ValueError("Remainder can only be computed when `tag_roll_up` is active")
        if ignore_dimensions:
            if type(ignore_dimensions) in (list, tuple, set):
                ignore_dimensions = set(ignore_dimensions)
            else:
                ignore_dimensions = {ignore_dimensions}
        else:
            ignore_dimensions = set()
        ret = {}
        q_filters = []
        prefixed_q_filters = []
        filter_prefix = self._get_relevant_accesslog_filter_prefix(remainder=remainder)
        for df in self.dimension_filters:
            if df.dimension in ignore_dimensions and not isinstance(df, TagDimensionFilter):
                # tag filters are not ignored even if they are for an ignored dimension
                continue
            # here a special case is when two report types are merged into one
            if (
                self.merge_report_types
                and isinstance(df, ForeignKeyDimensionFilter)
                and df.dimension == "report_type"
            ):
                if len(df.values) != 2:
                    raise SlicerConfigError(SlicerConfigErrorCode.E117)
                # we need to create a Q-based filter that will be used to filter the report types
                # that are involved in the query
                # we use the order of the report types to determine the main and fallback rts.
                rt1, rt2 = df.values
                # in import batch filters, we need to use the original report type ID,
                # not the materialized one, otherwise the check will fail
                orig_rt1 = self._mat_reports_map.get(rt1, rt1)
                filter_prefix2 = "relevant_accesslogs__"
                fallback_rt_subquery = ImportBatch.objects.filter(
                    report_type_id=orig_rt1,
                    platform_id=OuterRef("platform_id"),
                    organization_id=OuterRef("organization_id"),
                    date=OuterRef("date"),
                    record_count__gt=0,
                )
                prefixed_rt_subquery = ImportBatch.objects.filter(
                    report_type_id=orig_rt1,
                    platform_id=OuterRef(f"{filter_prefix2}platform_id"),
                    organization_id=OuterRef(f"{filter_prefix2}organization_id"),
                    date=OuterRef(f"{filter_prefix2}date"),
                    record_count__gt=0,
                )
                q_filters.append(
                    Q(report_type_id=rt1) | (Q(report_type_id=rt2) & ~Exists(fallback_rt_subquery))
                )
                prefixed_q_filters.append(
                    Q(**{f"{filter_prefix}report_type_id": rt1})
                    | (Q(**{f"{filter_prefix}report_type_id": rt2}) & ~Exists(prefixed_rt_subquery))
                )
                continue
            # normal case
            ret.update(df.query_params(clickhouse_compatible=use_clickhouse))
        logger.debug("filters: %s", ret)
        logger.debug("q_filters: %s", q_filters)
        logger.debug("prefixed_q_filters: %s", prefixed_q_filters)
        if self.organization_filter is not None:
            # convert organization filter to a list of ids for easier compatibility with
            # clickhouse and for simpler query (even though that is not a big deal)
            org_filter_pks = self._resolve_extra_organization_filter_to_pks()
            if "organization_id__in" in ret:
                orig_orgs = set(ret["organization_id__in"])
                ret["organization_id__in"] = list(orig_orgs & org_filter_pks)
            else:
                ret["organization_id__in"] = list(org_filter_pks)
        logger.debug("filters with org: %s", ret)
        return ret, q_filters, prefixed_q_filters

    def _resolve_extra_organization_filter_to_pks(self) -> Set[int]:
        if self.organization_filter is None:
            return set()
        if type(self.organization_filter) in (list, tuple, set):
            return set(self.organization_filter)
        return set(self.organization_filter.values_list("pk", flat=True))

    def add_extra_organization_filter(self, org_filter: Iterable):
        self.organization_filter = org_filter

    def add_filter(self, dimension_filter: DimensionFilter, add_group=False):
        self.dimension_filters.append(dimension_filter)
        if add_group:
            if self.trend_mode:
                raise ValueError("Cannot group by dimension when trend_mode is True")
            self.group_by.append(dimension_filter.dimension)

    def add_group_by(self, dimension):
        if self.trend_mode:
            raise ValueError("Cannot group by dimension when trend_mode is True")
        self.group_by.append(dimension)

    def add_split_by(self, dimension):
        self.split_by.append(dimension)

    @classmethod
    def _validate_dim_compatible_with_all_rts(cls, dim_name: str, rts: List[ReportType]):
        dim_obj = rts[0].dimension_by_attr_name(dim_name)
        for rt in rts[1:]:
            if dim_obj not in rt.dimensions_sorted:
                raise SlicerConfigError(SlicerConfigErrorCode.E100)

    def check_params(self):
        """
        Checks that the config makes sense and data could be retrieved
        """
        rt_filter = []
        for fltr in self.dimension_filters:
            if isinstance(fltr, ForeignKeyDimensionFilter) and fltr.dimension == "report_type":
                rt_filter = fltr.values
        if len(rt_filter) != 1:
            if not rt_filter and self.merge_report_types:
                # there must be a filter on report type when merging report types
                raise SlicerConfigError(SlicerConfigErrorCode.E119)
            # more than one RT is selected, we need to make sure explicit dimensions are the
            # same for all RTs
            rts = ReportType.objects.all()
            if rt_filter:
                rts = rts.filter(pk__in=rt_filter)
            for dim_name in self.group_by:
                if dim_name.startswith("dim"):
                    self._validate_dim_compatible_with_all_rts(dim_name, rts)
            for fltr in self.dimension_filters:
                if isinstance(fltr, ExplicitDimensionFilter):
                    self._validate_dim_compatible_with_all_rts(fltr.dimension, rts)

        # if multiple primary dimensions are used, some features are not supported
        if len(self.primary_dimensions) > 1:
            if self.tag_roll_up:
                raise SlicerConfigError(SlicerConfigErrorCode.E114)
            if self.include_all_zero_rows and not self.trend_mode:
                raise SlicerConfigError(SlicerConfigErrorCode.E115)

        if self.trend_mode:
            if not self.base_subset_filters or not self.compared_subset_filters:
                raise SlicerConfigError(SlicerConfigErrorCode.E120)

        # when merge_report_types is True, split by report type is not supported
        if self.merge_report_types and "report_type" in self.split_by:
            raise SlicerConfigError(SlicerConfigErrorCode.E121)

    def check_params_for_data_query(self):
        """
        Extra checks to be performed before data query is run. These do not apply to other
        functions, such as getting possible dimension values.
        """
        if not self.group_by and not self.trend_mode:
            raise SlicerConfigError(SlicerConfigErrorCode.E106)

    def _get_relevant_accesslog_filter_prefix(self, remainder: bool = False) -> str:
        """
        Returns the prefix for the accesslog filter.
        When `remainder` is True, the prefix is "accesslog__" instead of "target__accesslog__",
        because the remainder is calculated relative to the tagged objects, not the tag itself.
        """
        if self.tag_roll_up:
            assert len(self.primary_dimensions) == 1, "one primary dimension is enforced elsewhere"
            field, _ = AccessLog.get_dimension_field(self.primary_dimensions[0])
            assert isinstance(field, ForeignKey), (
                "When tag roll up is active, the primary dimension must be a foreign key"
            )
            if remainder:
                return "accesslog__"
            primary_cls = field.remote_field.model
            tag_scope = TagClass.tag_scope_from_target_class(primary_cls)
            target_attr = Tag.target_attr_from_scope(tag_scope)
            return f"{target_attr}__accesslog__"
        return "accesslog__"

    def get_queryset(self, part: Optional[list] = None):
        self.check_params()
        self.check_params_for_data_query()
        self.check_part(part)

        filters, q_filters, prefixed_q_filters = self.create_filters()
        if part:
            for dim, value in zip(self.split_by, part, strict=True):
                fltr = self.filter_instance(dim, value)
                filters.update(fltr.query_params())

        # parameter to remember if we are going to query the accesslog table directly or
        # use a related model (e.g. Tag or Organization) and join accesslog to it.
        direct_accesslog_query = True

        if len(self.primary_dimensions) == 1:
            # we can use the old single-dimension logic
            primary_dim = self.primary_dimensions[0]
            field, modifier = AccessLog.get_dimension_field(primary_dim)
            if isinstance(field, ForeignKey):
                primary_cls = field.remote_field.model
                if self.tag_roll_up:
                    # we will be summing up by tag, so the query is a bit different
                    # (slightly similar to mapped primary dimension)
                    tag_scope = TagClass.tag_scope_from_target_class(primary_cls)
                    tag_filters = [self.tag_filter] if self.tag_filter else []
                    relevant_accesslog_filter_prefix = self._get_relevant_accesslog_filter_prefix()
                    if self.tag_class:
                        tag_filters.append(Q(tag_class_id=self.tag_class))
                    # if we apply the tag filter on the qs itself, it for some reason creates
                    # an extremely slow query (at least on K1), maybe because joins with
                    # organization created for organization specific tags
                    # If we resolve the tags beforehand and use the pks, the query is much faster
                    tag_ids = set(
                        Tag.objects.filter(*tag_filters, tag_class__scope=tag_scope).values_list(
                            "pk", flat=True
                        )
                    )
                    qs = (
                        Tag.objects.filter(pk__in=tag_ids)
                        .annotate(
                            relevant_accesslogs=FilteredRelation(
                                relevant_accesslog_filter_prefix.rstrip("_"),
                                condition=Q(
                                    *prefixed_q_filters,
                                    **extend_query_filter(
                                        filters, relevant_accesslog_filter_prefix
                                    ),
                                ),
                            )
                        )
                        .values("pk")
                    )
                    direct_accesslog_query = False
                elif self.include_all_zero_rows and not self.trend_mode:
                    # we need to put the primary dimension model into play because zero usage is
                    # requested, or we are sorting by the primary dimension
                    qs = primary_cls.objects.all()
                    if primary_cls is Organization and self.organization_filter is not None:
                        qs = qs.filter(pk__in=self.organization_filter)
                    pk_annotation = {}
                    # deal with materialized report type mapping
                    if primary_dim == "report_type" and self._mat_reports_map:
                        whens = [
                            When(then=Value(orig), pk=pk)
                            for pk, orig in self._mat_reports_map.items()
                        ]
                        pk_annotation["pk"] = Case(
                            *whens, default=F("pk"), output_field=IntegerField()
                        )
                    relevant_accesslog_filter_prefix = self._get_relevant_accesslog_filter_prefix()

                    qs = (
                        qs.filter(**self._primary_dimension_filter())
                        .annotate(
                            relevant_accesslogs=FilteredRelation(
                                relevant_accesslog_filter_prefix.rstrip("_"),
                                condition=Q(
                                    *prefixed_q_filters,
                                    **extend_query_filter(
                                        filters, relevant_accesslog_filter_prefix
                                    ),
                                ),
                            )
                        )
                        .annotate(**pk_annotation)
                        .values("pk")
                    )
                    self._primary_dimension_query = True
                    direct_accesslog_query = False
                else:
                    # zero usage is not needed - we can just aggregate the accesslogs, which can be
                    # much faster
                    pk_def = F(primary_dim)
                    # deal with materialized report type mapping
                    if primary_dim == "report_type" and self._mat_reports_map:
                        whens = [
                            When(then=Value(orig), **{primary_dim: pk})
                            for pk, orig in self._mat_reports_map.items()
                        ]
                        pk_def = Case(*whens, default=pk_def, output_field=IntegerField())

                    qs = (
                        AccessLog.objects.filter(*q_filters, **filters)
                        .annotate(pk=pk_def)
                        .values("pk")
                        .distinct()
                    )
            elif field and primary_dim.startswith("dim"):
                qs = (
                    AccessLog.objects.filter(*q_filters, **filters)
                    .annotate(pk=F(primary_dim))
                    .values("pk")
                    .distinct()
                )
            elif field and isinstance(field, DateField):
                if modifier and modifier != "year":
                    raise ValueError(
                        'The only modifier allowed for date is "year", i.e. date__year'
                    )
                qs = (
                    AccessLog.objects.filter(*q_filters, **filters)
                    .annotate(pk=F(primary_dim))
                    .values("pk")
                    .distinct()
                )
            elif field:
                raise SlicerConfigError(
                    SlicerConfigErrorCode.E102,
                    message=f"Primary dimension {primary_dim} is not supported",
                    details={"dimension": primary_dim},
                )
            else:
                raise SlicerConfigError(
                    SlicerConfigErrorCode.E103,
                    message=f"Primary dimension {primary_dim} is not valid",
                    details={"dimension": primary_dim},
                )
        else:
            # we need to use the new multi-index logic
            annots = {}
            for i, dim in enumerate(self.primary_dimensions):
                dim_key = self.get_pk_key(i)
                annot = F(dim)
                # deal with materialized report type mapping
                if dim == "report_type" and self._mat_reports_map:
                    whens = [
                        When(then=Value(orig), report_type_id=pk)
                        for pk, orig in self._mat_reports_map.items()
                    ]
                    annot = Case(*whens, default=annot, output_field=IntegerField())
                annots[dim_key] = annot

            qs = (
                AccessLog.objects.filter(*q_filters, **filters)
                .annotate(**annots)
                .values(*annots.keys())
                .distinct()
            )
        # common stuff for both single and multi-index logic
        qs = qs.annotate(
            **self._prepare_annotations(
                accesslog_prefix="" if direct_accesslog_query else "relevant_accesslogs__"
            )
        )
        if not self.include_all_zero_rows:
            # total is added in _prepare_annotations and is a sum of all the value columns
            qs = qs.filter(_total__gt=0)
        elif self.trend_mode:
            # in trend mode, we need to filter out rows where both base and compared are zero
            # even if include_all_zero_rows is True
            qs = qs.exclude(base=0, compared=0)
        if self.merge_report_types:
            # we need to remap used materialized report type IDs to the original ones
            relevant_accesslog_filter_prefix = "relevant_accesslogs__" if self.tag_roll_up else ""
            qs = qs.alias(
                orig_report_type_id=Case(
                    *[
                        When(
                            then=Value(orig),
                            **{f"{relevant_accesslog_filter_prefix}report_type_id": pk},
                        )
                        for pk, orig in self._mat_reports_map.items()
                    ],
                    default=F(f"{relevant_accesslog_filter_prefix}report_type_id"),
                    output_field=IntegerField(),
                )
            ).annotate(
                used_rts=ArrayAgg(
                    "orig_report_type_id",
                    distinct=True,
                    filter=Q(orig_report_type_id__isnull=False),
                )
            )
        return qs

    def _primary_dimension_filter(self) -> dict:
        ret = {}
        for df in self.dimension_filters:
            if df.dimension in self.primary_dimensions:
                ret.update(df.query_params(primary_filter=True))
        return ret

    def _prepare_annotations(self, accesslog_prefix="relevant_accesslogs__") -> dict:
        if self.trend_mode:

            def getQ(subset_filters: List[DimensionFilter]):
                return reduce(
                    operator.and_,
                    (
                        Q(**extend_query_filter(f.query_params(), accesslog_prefix))
                        for f in subset_filters
                    ),
                )

            def coal_sum(sum_filter):
                return Coalesce(Sum(f"{accesslog_prefix}value", filter=sum_filter), 0)

            annotations = {
                self.COL_BASE: coal_sum(getQ(self.base_subset_filters)),
                self.COL_COMPARED: coal_sum(getQ(self.compared_subset_filters)),
                # For trend mode, we use the base as the total because total is used to determine
                # if the row will be included in when `include_all_zero_rows` is True.
                # We want to influence if rows with starting zero usage are included or not
                # because these rows generate infinite relative difference which may be
                # undesired in some cases
                self.COL_TOTAL: coal_sum(getQ(self.base_subset_filters)),
                self.COL_DIFF: F("compared") - F("base"),
                self.COL_REL_DIFF: (1.0 * F("compared") - F("base")) / NullIf(F("base"), 0),
            }
        else:
            gb_query = self.get_possible_groups_queryset()
            if not gb_query:
                return {
                    "total": Coalesce(Sum(f"{accesslog_prefix}value"), 0),
                    self.COL_TOTAL: Coalesce(Sum(f"{accesslog_prefix}value"), 0),
                }
            if gb_query.count() > settings.REPORTING_MAXIMUM_POSSIBLE_COLUMNS:
                raise SlicerConfigError(
                    SlicerConfigErrorCode.E101,
                    message=f"There are too many ({gb_query.count()}) possible groups, please "
                    "refine your configuration",
                    details={"group_count": gb_query.count()},
                )
            if gb_query.count() == 0:
                return {}
            # we have some group_by values, but not too many
            annotations = {}
            for group in gb_query:
                key = self._group_dict_to_group_key(group)
                filters = {f"{accesslog_prefix}{dim}": group[dim] for dim in self.group_by}
                annotations[key] = Coalesce(Sum(f"{accesslog_prefix}value", filter=Q(**filters)), 0)
                annotations[self.COL_TOTAL] = Coalesce(Sum(f"{accesslog_prefix}value"), 0)
        self._annotations = annotations
        return annotations

    def _group_dict_to_group_key(self, group: dict) -> str:
        keys = []
        for dim in self.group_by:
            key = group[dim]
            if dim == "report_type":
                # we want to map from a potentially materialized report type to the original one
                key = self._mat_reports_map.get(key, key)
            keys.append(key)
        return "grp-" + ",".join(map(str, keys))

    def decode_key(self, key: str) -> dict:
        if not key.startswith("grp-"):
            raise ValueError('Key must start with "grp-"')
        # 'None' can happen if we group by dimension that is not used and thus has no values
        # present
        pks = [None if x == "None" else (int(x) if "-" not in x else x) for x in key[4:].split(",")]
        return OrderedDict([(dim, pks[i]) for (i, dim) in enumerate(self.group_by)])

    @classmethod
    def _text_to_filter(cls, text, text_fields=("name",)):
        return reduce(
            operator.or_, (Q(**{f"{text_field}__ilike": text}) for text_field in text_fields)
        )

    def create_text_filter(self, dimension, text_filter, clickhouse_compatible=False) -> dict:
        """
        Creates a dict that can be used in queryset filter to filter only those instances of
        `dimension` which contain the text from `text_filter`.

        If `clickhouse_compatible` is True, the filter query will be resolved to a list of ids,
        otherwise it will remain as a subquery. The former is useful for clickhouse, the latter
        is faster if normal django ORM is used.
        """
        field, modifier = AccessLog.get_dimension_field(dimension)
        if isinstance(field, ForeignKey):
            primary_cls = field.remote_field.model
            subfilter = primary_cls.objects.filter(self._text_to_filter(text_filter)).values_list(
                "pk", flat=True
            )
            if clickhouse_compatible:
                if subfilter.count() > CLICKHOUSE_ID_COUNT_LIMIT:
                    raise ClickhouseIncompatibleFilter("Too many ids to resolve")
                subfilter = list(subfilter)
            extra_filter = {f"{dimension}_id__in": subfilter}
        elif field and dimension.startswith("dim"):
            subfilter = DimensionText.objects.filter(
                self._text_to_filter(text_filter, text_fields=("text", "text_local"))
            ).values_list("pk", flat=True)
            if clickhouse_compatible:
                if subfilter.count() > CLICKHOUSE_ID_COUNT_LIMIT:
                    raise ClickhouseIncompatibleFilter("Too many ids to resolve")
                subfilter = list(subfilter)
            extra_filter = {f"{dimension}__in": subfilter}
        else:
            raise SlicerConfigError(SlicerConfigErrorCode.E107)
        return extra_filter

    @classmethod
    def create_pk_filter(cls, dimension, pks: list) -> dict:
        """
        Creates a dict that can be used in queryset filter to filter only those instances of
        `dimension` which have their pk in the list of `pks`.
        """
        field, modifier = AccessLog.get_dimension_field(dimension)
        if isinstance(field, ForeignKey):
            extra_filter = {f"{dimension}_id__in": pks}
        elif field and dimension.startswith("dim"):
            extra_filter = {f"{dimension}__in": pks}
        else:
            raise SlicerConfigError(SlicerConfigErrorCode.E107)
        return extra_filter

    def get_possible_dimension_values_clickhouse(
        self, dimension, max_values_count=100, ignore_self=False, text_filter=None, pks=None
    ):
        # the following can throw a ClickhouseIncompatibleFilter exception
        # if some of the normal filters are not supported by clickhouse
        query = self.get_possible_dimension_values_queryset(
            dimension, ignore_self=ignore_self, use_clickhouse=True
        )
        if text_filter:
            # when filtering by text, we must first resolve the IDs of the matched objects
            # and then use them in the clickhouse query. Because there is a limit on the
            # number of IDs that can be passed to clickhouse, we must check against such limit
            # and if it is exceeded, we must use the django ORM
            # the following can throw a ClickhouseIncompatibleFilter exception
            tf = self.create_text_filter(dimension, text_filter, clickhouse_compatible=True)
            query = query.filter(**tf)
        if pks:
            query = query.filter(**self.create_pk_filter(dimension, pks))

        count = ch_backend.get_count(query)
        cropped = False
        if max_values_count and count > max_values_count:
            cropped = True
            query = query[:max_values_count]
        result = ch_backend.get_records(query)
        # the output should not contain the _id suffix for foreign key fields,
        # but it is contained in clickhouse names, so we need to remap it
        data = [
            {(k if k != f"{dimension}_id" else dimension): v for k, v in rec._asdict().items()}
            for rec in result
        ]
        return {"count": count, "values": data, "cropped": cropped}

    def get_possible_dimension_values(
        self, dimension, max_values_count=100, ignore_self=False, text_filter=None, pks=None
    ):
        """
        For a given dimension it returns which values are present in the filtered data and can thus
        be filtered/grouped on.
        If `ignore_self` is True, the dimensions themselves will not be used in the filter.
        """
        if self.use_clickhouse:
            try:
                return self.get_possible_dimension_values_clickhouse(
                    dimension,
                    max_values_count=max_values_count,
                    ignore_self=ignore_self,
                    text_filter=text_filter,
                    pks=pks,
                )
            except ClickhouseIncompatibleFilter:
                # clickhouse cannot be used for this case, fall back to django ORM
                #
                # Note: this should only happen if the query involves too many tagged titles
                # or a very loose text filter, so it should not be a common case
                # and the processing will take so long that this extra processing will
                # not be noticeable
                pass

        # normal django query
        # we can ignore primary because it does not have any influence on the filtering
        self._replace_report_type_with_materialized(
            extra_dimensions_to_preserve={dimension}, ignore_primary=True
        )
        query = self.get_possible_dimension_values_queryset(dimension, ignore_self=ignore_self)
        # add text filter
        if text_filter:
            extra_filter = self.create_text_filter(dimension, text_filter)
            query = query.filter(**extra_filter)
        if pks:
            query = query.filter(**self.create_pk_filter(dimension, pks))
        # get count and decide if we need to sort
        try:
            logger.debug("Query: %s", query.query)
        except EmptyResultSet:
            logger.debug("Query: EmptyResultSet")
        count = query.count()
        cropped = False
        if max_values_count and count > max_values_count:
            cropped = True
            query = query.annotate(score=Coalesce(Sum("value"), 0)).order_by("-score")
            query = query[:max_values_count]
        return {"count": count, "values": list(query), "cropped": cropped}

    def get_possible_dimension_values_queryset(
        self, dimensions, ignore_self=False, use_clickhouse=False
    ):
        if type(dimensions) not in (tuple, list, set):
            dimensions = [dimensions]
        ignore_dimensions = dimensions if ignore_self else None
        self.check_params()
        query_params, q_filters, _ = self.create_filters(
            ignore_dimensions=ignore_dimensions, use_clickhouse=use_clickhouse
        )
        if use_clickhouse and not q_filters:
            # TODO: clickhouse version is not compatible with q_filters at this point
            # clickhouse uses column names with the _id suffix
            dims = [
                f"{dim}_id" if f"{dim}_id" in AccessLogCube._dimensions else dim
                for dim in dimensions
            ]
            query = (
                AccessLogCube.query()
                .filter(**query_params)
                .group_by(*dims)
                .aggregate(score=HSum("value"))
                .order_by("-score")
            )
        else:
            # check if we could use a materialized rt
            if len(rt_fltr := query_params.get("report_type_id__in", [])) == 1:
                # we can only use it if there is one RT
                rt = ReportType.objects.get(pk=rt_fltr[0])
                used_dimensions = {
                    dim.split("__")[0] for dim in query_params.keys() if dim != "report_type_id__in"
                }
                used_dimensions |= set(dimensions)
                used_dimensions = [
                    dim[:-3] if dim.endswith("_id") else dim for dim in used_dimensions
                ]
                if new_rt := find_best_materialized_view(rt, used_dimensions):
                    query_params["report_type_id__in"] = [new_rt.pk]
            query = (
                AccessLog.objects.filter(*q_filters, **query_params).values(*dimensions).distinct()
            )

        return query

    def get_possible_groups_queryset(self):
        if self.group_by:
            return self.get_possible_dimension_values_queryset(self.group_by)
        return None

    def get_parts_queryset(self, use_clickhouse=False):
        """
        This can return either a CubeQuery or a Django queryset. The calling code should be able
        to handle both cases. Even if `use_clickhouse` is True, the returned queryset may be a
        Django queryset if the query is too complex for clickhouse.
        """
        if self.split_by:
            try:
                return self.get_possible_dimension_values_queryset(
                    self.split_by, use_clickhouse=use_clickhouse
                )
            except ClickhouseIncompatibleFilter:
                # clickhouse cannot be used for this case, fall back to django ORM
                #
                # Note: this should only happen if the query involves too many tagged titles
                # or a very loose text filter, so it should not be a common case
                return self.get_possible_dimension_values_queryset(
                    self.split_by, use_clickhouse=False
                )
        return None

    def get_data(self, lang="en", part: Optional[list] = None) -> QuerySet[dict]:
        """
        :param lang: language in which texts should be obtained - influences sorting
        :param part: when `split_by` is set, this defines for which part the result should be
                     obtained. It should be a list of the same length as `split_by`
        """
        # we do the following just before getting data in order to ensure the slicer is finalized
        # TODO: we could lock the slicer for further changes after that
        self._replace_report_type_with_materialized()
        qs = self.get_queryset(part=part)
        obs = []
        for i, ob in enumerate(self.order_by):
            prefix = "-" if ob.startswith("-") else ""
            ob = ob.lstrip("-")
            if ob == "tag" and self.tag_roll_up:
                obs.append(prefix + "name")
            elif ob.startswith("dim"):
                # when sorting by dimX we need to map the IDs to the corresponding texts
                # because the mapping does not use a Foreign key relationship, we use a subquery
                dt_query = DimensionText.objects.filter(id=OuterRef(ob)).values("text")[:1]
                qs = qs.alias(**{ob + "sort": Subquery(dt_query)})
                obs.append(prefix + ob + "sort")
            elif ob.startswith("grp-"):
                if ob not in self._annotations:
                    # we ignore sort groups that are not in the data
                    logger.debug('Ignoring unknown order by "%s"', ob)
                else:
                    obs.append(prefix + ob)
            elif self.trend_mode and ob in self.TREND_MODE_COLS:
                # implicit columns created for period-over-period
                obs.append(prefix + ob)
            elif (
                ob in self.primary_dimensions and not ob.startswith("date") and not self.tag_roll_up
            ):
                # when not querying the related model, we need to prefix the field name with the
                # dimension name to join to the related model to the AccessLog model
                dim_prefix = "" if self._primary_dimension_query else f"{ob}__"

                if ob == "target":
                    # title does not have `short_name`, just `name`
                    obs.append(prefix + dim_prefix + "name")
                else:
                    # if there is a name, we want name, if not, we want short_name
                    # the following simulates this
                    qs = qs.alias(
                        **{
                            f"sort_name{i}": Concat(
                                F(f"{dim_prefix}name_{lang}"),
                                F(f"{dim_prefix}short_name"),
                                output_field=CharField(),
                            )
                        }
                    )
                    obs.append(prefix + f"sort_name{i}")
            elif (
                any(ob.startswith(primary_dim) for primary_dim in self.primary_dimensions)
                and not self.tag_roll_up
            ):
                if self._primary_dimension_query:
                    # we are querying the related model, not accesslog, we need to process the
                    # order by definition
                    start, *rest, end = ob.split("__")
                    obs.append(prefix + end)
                else:
                    # we do not validate this, so it could be a problem, but it would crash rather
                    # than produce wrong results, so we leave it as is
                    obs.append(prefix + ob)
            elif ob == self.COL_TOTAL:
                # ordering by the row totals (the column called `COL_TOTAL`)
                obs.append(prefix + self.COL_TOTAL)
            else:
                # this means that the order by is not consistent with the rest of the query
                # it would be prudent to raise an error, but there are already existing data
                # which have this problem, so we just ignore it and drop the ordering
                logger.error('Dropping inconsistent order by "%s"', ob)
        qs = qs.order_by(*obs)
        try:
            logger.debug("Slicer query: %s", qs.query)
        except EmptyResultSet:
            logger.debug("Slicer query: empty")
        return qs

    def get_remainder(self, part: Optional[list] = None) -> dict:
        """
        In case `tag_roll_up` is active, this gets the remaining usage for untagged objects.
        Because it would be complicated to make it part of the standard interface provided
        by `get_data`, we have a separate method for it.

        :param part: when `split_by` is set, this defines for which part the result should be
        obtained. It should be a list of the same length as `split_by`
        """
        # handle part and split_by
        self.check_part(part)

        field, modifier = AccessLog.get_dimension_field(self.primary_dimensions[0])
        if isinstance(field, ForeignKey):
            primary_cls = field.remote_field.model
            if self.tag_roll_up:
                tag_scope = TagClass.tag_scope_from_target_class(primary_cls)
                tag_filters = [self.tag_filter] if self.tag_filter else []
                if self.tag_class:
                    tag_filters.append(Q(tag_class_id=self.tag_class))
                # find all untagged objects
                # tag_scope.value is used to enforce string value - cachalot does not like enums
                qs = primary_cls.objects.exclude(
                    tags__in=Tag.objects.filter(*tag_filters, tag_class__scope=tag_scope.value)
                )
                # apply the same filters that are used for the main query
                if primary_cls is Organization and self.organization_filter is not None:
                    qs = qs.filter(pk__in=self.organization_filter)
                # use the same query as for the main query when the primary object are annotated
                # but then aggregate everything to a single row
                filters, _, prefixed_q_filters = self.create_filters(remainder=True)
                if self.split_by and part:
                    for dim, value in zip(self.split_by, part, strict=True):
                        fltr = self.filter_instance(dim, value)
                        filters.update(fltr.query_params())
                final_annotations = self._prepare_annotations()
                if self.trend_mode:
                    # in trend mode, we add two columns which are based on other computed columns,
                    # it seems that .aggregate() cannot deal with that, so we need to remove them
                    # and compute the values in python later
                    del final_annotations[self.COL_DIFF]
                    del final_annotations[self.COL_REL_DIFF]
                result = (
                    qs.filter(**self._primary_dimension_filter())
                    .annotate(
                        relevant_accesslogs=FilteredRelation(
                            "accesslog",
                            condition=Q(
                                *prefixed_q_filters, **extend_query_filter(filters, "accesslog__")
                            ),
                        )
                    )
                    .values("pk")
                    .aggregate(**final_annotations)
                )
                if self.trend_mode:
                    # compute the two columns that were removed above
                    result[self.COL_DIFF] = result[self.COL_COMPARED] - result[self.COL_BASE]
                    result[self.COL_REL_DIFF] = (
                        (result[self.COL_DIFF] / result[self.COL_BASE])
                        if result[self.COL_BASE]
                        else None
                    )
                return result
            raise ValueError("Remainder can only be computed when `tag_roll_up` is active")
        # the following will happen if the primary dimension is not a foreign key
        # and thus cannot be one of the taggable models (Organization, Platform, Title)
        raise ValueError("Remainder can only be computed when primary dimension supports tags")

    def check_part(self, part):
        """
        Checks that the `split_by` definition is compatible with the part value given
        """
        if self.split_by:
            if not part:
                raise SlicerConfigError(SlicerConfigErrorCode.E108)
            if len(self.split_by) != len(part):
                raise SlicerConfigError(
                    SlicerConfigErrorCode.E109, details={"split_by": self.split_by, "part": part}
                )
        elif part:
            # part cannot be used if `split_by` is not set up
            raise SlicerConfigError(SlicerConfigErrorCode.E110)

    def resolve_explicit_dimension(self, dim_ref: str) -> Optional[Dimension]:
        rts = self.involved_report_types()
        if rts:
            # the dimension should be common to all report types
            # but we want to ensure that
            dims = {rt.dimension_by_attr_name(dim_ref) for rt in rts}
            if len(dims) > 1:
                raise SlicerConfigError(SlicerConfigErrorCode.E113)
            return dims.pop()
        return None

    def involved_report_types(self) -> List[ReportType]:
        """
        Returns a list of report types that are part of the query if there is any filter on them.
        If there is no filter, all report types are returned.
        This method preserves the order of the report types as they are defined in the filter.
        """
        rt_fltr = None
        for fltr in self.dimension_filters:
            if fltr.dimension == "report_type":
                rt_fltr = fltr
                break
        if rt_fltr:
            query_params = rt_fltr.query_params(primary_filter=True)
            pk_to_rt = {rt.pk: rt for rt in ReportType.objects.filter(**query_params)}
            return [pk_to_rt[pk] for pk in rt_fltr.values if pk in pk_to_rt]
        return list(ReportType.objects.exclude_materialized())

    def _replace_report_type_with_materialized(
        self, extra_dimensions_to_preserve=None, ignore_primary=False
    ):
        rts = self.involved_report_types()
        for rt in rts:
            dimensions = self._involved_dimensions(ignore_primary=ignore_primary)
            if extra_dimensions_to_preserve:
                dimensions |= set(extra_dimensions_to_preserve)
            materialized_report = find_best_materialized_view(rt, dimensions)
            if materialized_report:
                logger.info("Using materialized report: %s instead of %s", materialized_report, rt)
                self._mat_reports_map[materialized_report.pk] = rt.pk
                for fltr in self.dimension_filters:
                    if fltr.dimension == "report_type":
                        fltr.values = [
                            materialized_report.pk if rt.pk == val else val for val in fltr.values
                        ]

    def _involved_dimensions(self, ignore_primary=False) -> Set[str]:
        """
        Returns a set of dimensions that are involved in the query.
        """
        dimensions = {fltr.dimension for fltr in self.dimension_filters}
        if not ignore_primary:
            dimensions.update(self.primary_dimensions)
        dimensions.update({dim.lstrip("-") for dim in self.order_by})
        dimensions.update(self.group_by)
        dimensions.update(self.split_by)
        return dimensions

    @classmethod
    def filter_class(cls, dimension) -> Type[DimensionFilter]:
        """
        Finds the right Filter class for the dimension at hand
        """
        if dimension.startswith("tag__"):
            return TagDimensionFilter
        if dimension.startswith("tag_class__"):
            return TagClassDimensionFilter
        field, _modifier = AccessLog.get_dimension_field(dimension)
        if isinstance(field, ForeignKey):
            return ForeignKeyDimensionFilter
        elif isinstance(field, DateField):
            return DateDimensionFilter
        elif isinstance(field, IntegerField):
            return ExplicitDimensionFilter
        else:
            raise ValueError(f"not supported yet ({dimension}, {field}, {_modifier})")

    @classmethod
    def filter_instance(cls, dimension: str, value):
        """
        Uses `filter_class` to get the correct filter class for dimension and then creates
        an instance of the filter for `value`.
        """
        filter_class = cls.filter_class(dimension)
        if filter_class is DateDimensionFilter:
            field, _modifier = AccessLog.get_dimension_field(dimension)
            if isinstance(value, datetime.date):
                # specific date means we should only allow the one month
                return filter_class(field.name, start=value, end=value)
            if isinstance(value, int):
                # we treat int in a special way as the whole year with that number
                value = {"start": f"{value}-01-01", "end": f"{value}-12-31"}
            elif isinstance(value, str):
                start = parse_month(value)
                end = month_end(start)
                value = {"start": start, "end": end}
            return filter_class(field.name, *date_range_from_params(value))
        elif filter_class is TagDimensionFilter:
            dimension = dimension[len("tag__") :]  # noqa E203
            return filter_class(dimension, value)
        elif filter_class is TagClassDimensionFilter:
            dimension = dimension[len("tag_class__") :]  # noqa E203
            return filter_class(dimension, value)
        else:
            return filter_class(dimension, value)

    @classmethod
    def create_from_params(cls, params: dict) -> "FlexibleDataSlicer":
        """
        Takes the parameters as they would be obtained from the API and creates a new slicer
        instance based on those.
        """
        # Handle both old primary_dimension and new primary_dimensions parameters
        if primary_dimensions := params.get("primary_dimensions"):
            primary_dimensions = parse_b64json(primary_dimensions)
        else:
            primary_dimensions = params.get("primary_dimension")
        if not primary_dimensions:
            raise SlicerConfigError(SlicerConfigErrorCode.E104)
        slicer = cls(primary_dimensions)
        # filters
        filters = params.get("filters")
        filters = parse_b64json(filters) if filters else {}
        for key, value in filters.items():
            slicer.add_filter(cls.filter_instance(key, value))
        # groups
        groups = params.get("groups")
        groups = parse_b64json(groups) if groups else []
        for group in groups:
            slicer.add_group_by(group)
        # trend mode
        if trend_mode := to_bool(params.get("trend_mode")):
            slicer.trend_mode = trend_mode

            def make_filters(params_name):
                if fltrs := params.get(params_name):
                    fltrs = parse_b64json(fltrs)
                    if "date" in fltrs:
                        return [cls.filter_instance("date", fltrs["date"])]
                return None

            slicer.base_subset_filters = (
                make_filters("base_subset_filters") or slicer.base_subset_filters
            )
            slicer.compared_subset_filters = (
                make_filters("compared_subset_filters") or slicer.compared_subset_filters
            )
        # split by
        splits = params.get("split_by")
        splits = parse_b64json(splits) if splits else []
        for split in splits:
            slicer.add_split_by(split)
        # ordering
        if order_by := params.get("order_by"):
            slicer.order_by = [order_by]
        # extra stuff
        # the zero_rows value should be recoded to python bool, but we want to make sure
        slicer.include_all_zero_rows = to_bool(params.get("zero_rows", ""))
        slicer.include_row_totals = to_bool(params.get("row_totals", ""))
        slicer.include_col_totals = to_bool(params.get("col_totals", ""))
        slicer.tag_roll_up = to_bool(params.get("tag_roll_up", ""))
        if tag_class := params.get("tag_class"):
            slicer.tag_class = int(tag_class)
        slicer.show_untagged_remainder = to_bool(params.get("show_untagged_remainder", ""))
        slicer.merge_report_types = to_bool(params.get("merge_report_types", ""))
        return slicer

    @classmethod
    def create_from_config(cls, params: dict) -> "FlexibleDataSlicer":
        """
        Takes the output of self.config() and converts it into a slicer instance
        """
        # Handle both old primary_dimension and new primary_dimensions parameters
        primary_dimensions = params.get("primary_dimensions")
        if not primary_dimensions:
            # Fallback to old parameter name for backward compatibility
            primary_dimensions = params.get("primary_dimension")
            if not primary_dimensions:
                raise SlicerConfigError(SlicerConfigErrorCode.E104)
        slicer = cls(primary_dimensions)
        # filters
        filters = params.get("filters", [])
        for fltr in filters:
            slicer.add_filter(cls._config_dict_to_filter(fltr))
        # groups
        slicer.group_by = params.get("group_by", [])
        # split by
        slicer.split_by = params.get("split_by", [])
        # ordering
        slicer.order_by = params.get("order_by", [])
        # extra stuff
        slicer.include_all_zero_rows = params.get("zero_rows", False)
        slicer.include_row_totals = params.get("row_totals", False)
        slicer.include_col_totals = params.get("col_totals", False)
        slicer.tag_roll_up = params.get("tag_roll_up", False)
        slicer.tag_class = params.get("tag_class")
        slicer.show_untagged_remainder = params.get("show_untagged_remainder", False)
        # trend mode
        slicer.trend_mode = params.get("trend_mode", False)
        if slicer.trend_mode:
            slicer.base_subset_filters = [
                cls._config_dict_to_filter(fltr) for fltr in params.get("base_subset_filters", [])
            ]
            slicer.compared_subset_filters = [
                cls._config_dict_to_filter(fltr)
                for fltr in params.get("compared_subset_filters", [])
            ]
        # merge_report_types
        slicer.merge_report_types = params.get("merge_report_types", False)
        return slicer

    @classmethod
    def _config_dict_to_filter(cls, fltr: dict) -> DimensionFilter:
        dim = fltr["dimension"]
        if "tag_ids" in fltr:
            return TagDimensionFilter(dim, fltr["tag_ids"])
        elif "tag_class_ids" in fltr:
            return TagClassDimensionFilter(dim, fltr["tag_class_ids"])
        else:
            filter_class = cls.filter_class(dim)
            return (
                filter_class(dim, fltr["start"], fltr["end"])
                if filter_class is DateDimensionFilter
                else filter_class(dim, fltr["values"])
            )

    def filter_to_str(self, fltr):
        """
        Human-readable representation of the filter to be included in exports, etc.
        For some filters, we need context of the slicer to be able to serialize it, so it is here
        :param fltr:
        :return:
        """
        dim_to_str = {
            "target": _("Title"),
            "organization": _("Organization"),
            "platform": _("Platform"),
        }
        if isinstance(fltr, ExplicitDimensionFilter):
            dim = self.resolve_explicit_dimension(fltr.dimension)
            return f"{dim.short_name}: {fltr.value_str}"
        elif isinstance(fltr, ForeignKeyDimensionFilter):
            field, _modifier = AccessLog.get_dimension_field(fltr.dimension)
            return f"{field.remote_field.model._meta.verbose_name}: {fltr.value_str}"
        elif isinstance(fltr, DateDimensionFilter):
            field, _modifier = AccessLog.get_dimension_field(fltr.dimension)
            return f"{field.verbose_name}: {fltr.value_str}"
        elif isinstance(fltr, (TagDimensionFilter, TagClassDimensionFilter)):
            word = (
                ngettext("tag", "tags", len(fltr.tag_ids))
                if isinstance(fltr, TagDimensionFilter)
                else ngettext("tag class", "tag classes", len(fltr.tc_ids))
            )
            return f"{dim_to_str.get(fltr.dimension, fltr.dimension)} - {word}: {fltr.value_str}"
        raise NotImplementedError(f"Unsupported filter class: {fltr.__class__.__name__}")

    def _get_coverage_for_filters(self, **fltrs):
        """
        Applies the filters to `DataCoverageExtractor` and returns the total coverage over
        all report types involved in the slicer
        """
        coverage = {}
        for rt in self.involved_report_types():
            comp = DataCoverageExtractor(report_type=rt, split_by_date=False, **fltrs)
            cov_data = comp.get_coverage_data()
            rt_cov = cov_data.get((), {})  # empty tuple for no split-by
            coverage["ib_count"] = coverage.get("ib_count", 0) + rt_cov.get("ib_count", 0)
            coverage["ib_max"] = coverage.get("ib_max", 0) + rt_cov.get("ib_max", 0)
        if ib_max := coverage.get("ib_max", 0):
            coverage["ratio"] = coverage["ib_count"] / ib_max
        else:
            coverage["ratio"] = None
        return coverage

    def _get_coverage_for_filters_merged_report_types(self, **fltrs):
        """
        Applies the filters to `DataCoverageExtractor` and returns the total coverage over
        all report types involved in the slicer.
        This version is used when merge_report_types is True. It merges the coverage data
        together by individual months.
        """
        rts = self.involved_report_types()
        assert len(rts) == 2, (
            "Exactly two RTs must be involved when merging RTs - this is enforced elsewhere"
        )
        # `involved_report_types` preserves the order of the report types as they are defined in the
        # filter, so we can just use them as they are
        rt1, rt2 = rts
        comp = DataCoverageExtractor(
            report_type=rt1, fallback_report_type=rt2, split_by_date=False, **fltrs
        )
        cov = comp.get_coverage_data()
        return cov.get((), {})

    def get_coverage(self) -> Optional[dict]:
        """
        Returns the result of data coverage computation based on the filters applied to the slicer
        """
        # check that the involved report types are compatible with coverage
        if any(
            rt.short_name in settings.REPORT_TYPES_WITHOUT_COVERAGE
            for rt in self.involved_report_types()
        ):
            return None

        # resolve the filters
        platform_ids = None
        organization_ids = None
        coverage_filters = {}
        for fltr in self.dimension_filters:
            if isinstance(fltr, ForeignKeyDimensionFilter) or isinstance(fltr, TagDimensionFilter):
                pks = (
                    set(fltr.values)
                    if isinstance(fltr, ForeignKeyDimensionFilter)
                    else set(fltr.get_tagged_obj_pks_qs())
                )
                if fltr.dimension == "platform":
                    platform_ids = pks if platform_ids is None else (platform_ids | pks)
                elif fltr.dimension == "organization":
                    organization_ids = pks if organization_ids is None else (organization_ids | pks)
            elif isinstance(fltr, DateDimensionFilter):
                if not self.trend_mode:
                    coverage_filters.update({"start_month": fltr.start, "end_month": fltr.end})
                else:
                    logger.warning("Ignoring overall date filter in trend mode")

        if self.organization_filter:
            # apply the extra organization filter to the pks
            # in contrast to the other filters, this one is "anded" with the rest, not "ored"
            extra_ids = self._resolve_extra_organization_filter_to_pks()
            organization_ids = (
                extra_ids if organization_ids is None else organization_ids & extra_ids
            )

        if platform_ids is not None:
            coverage_filters.update({"platform": platform_ids})
        if organization_ids is not None:
            coverage_filters.update({"organization": organization_ids})

        cov_method = (
            self._get_coverage_for_filters_merged_report_types
            if self.merge_report_types
            else self._get_coverage_for_filters
        )
        if self.trend_mode:
            # in trend mode, we need to calculate coverage for both base and compared periods
            # separately
            def subset_filters(fltrs):
                for fltr in fltrs:
                    if isinstance(fltr, DateDimensionFilter):
                        return {"start_month": fltr.start, "end_month": fltr.end}
                return {}

            base_range = subset_filters(self.base_subset_filters)
            base_cov = cov_method(**base_range, **coverage_filters)
            compared_range = subset_filters(self.compared_subset_filters)
            compared_cov = cov_method(**compared_range, **coverage_filters)
            return {"base": base_cov, "compared": compared_cov}
        else:
            return {"overall": cov_method(**coverage_filters)}


class SlicerConfigErrorCode(Enum):
    E100 = "E100"
    E101 = "E101"
    E102 = "E102"
    E103 = "E103"
    E104 = "E104"
    E105 = "E105"
    E106 = "E106"
    E107 = "E107"
    E108 = "E108"
    E109 = "E109"
    E110 = "E110"
    E111 = "E111"
    E112 = "E112"
    E113 = "E113"
    E114 = "E114"
    E115 = "E115"
    E116 = "E116"
    E117 = "E117"
    E118 = "E118"
    E119 = "E119"
    E120 = "E120"
    E121 = "E121"

    def __str__(self):
        return self.value


class SlicerConfigError(Exception):
    code_to_message = {
        SlicerConfigErrorCode.E100: (
            "It is not possible to group by explicit dimension unless that dimension is shared by "
            "all selected report types."
        ),
        SlicerConfigErrorCode.E101: (
            "There are too many possible groups, please refine your configuration."
        ),
        SlicerConfigErrorCode.E102: "The specified primary dimension is not supported.",
        SlicerConfigErrorCode.E103: "The specified primary dimension is not valid.",
        SlicerConfigErrorCode.E104: (
            "The attribute 'primary_dimension' or 'primary_dimensions' must be present in the "
            "request and not be empty."
        ),
        SlicerConfigErrorCode.E105: "The attribute 'dimension' must be present in the request.",
        SlicerConfigErrorCode.E106: (
            "At least one dimension must be selected to define the output columns."
        ),
        SlicerConfigErrorCode.E107: "The queried dimension is not supported.",
        SlicerConfigErrorCode.E108: "Part is not specified and `split_by` is used.",
        SlicerConfigErrorCode.E109: "Part specification is incompatible with `split_by`.",
        SlicerConfigErrorCode.E110: "Part was specified without `split_by` being active.",
        SlicerConfigErrorCode.E111: "Only date filters are supported for subsets in trend mode.",
        SlicerConfigErrorCode.E112: (
            "There are too many possible parts, please refine you configuration."
        ),
        SlicerConfigErrorCode.E113: "Dimension is not common to all used report types.",
        SlicerConfigErrorCode.E114: (
            "Tag roll up is not supported when multiple primary dimensions are used."
        ),
        SlicerConfigErrorCode.E115: (
            "Include all zero rows is not supported when multiple primary dimensions are used."
        ),
        SlicerConfigErrorCode.E116: (
            "Trend mode is not supported when multiple primary dimensions are used."
        ),
        SlicerConfigErrorCode.E117: (
            "When merge_report_types is True, exactly two report types must be selected."
        ),
        SlicerConfigErrorCode.E118: (
            "Report type filter must be specified when explicit dimension filter is used."
        ),
        SlicerConfigErrorCode.E119: (
            "When merging report types, an explicit report type filter must be specified."
        ),
        SlicerConfigErrorCode.E120: (
            "Both base and compared subset filters must be specified when trend_mode is True"
        ),
        SlicerConfigErrorCode.E121: (
            "Split by report type is not supported when merge_report_types is True."
        ),
    }

    def __init__(self, code: SlicerConfigErrorCode, *args, message=None, details=None, **kwargs):
        self.message = message or self.code_to_message[code]
        self.code = code.value
        self.details = details
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"SlicerConfigError {self.code}: {self.message}"
