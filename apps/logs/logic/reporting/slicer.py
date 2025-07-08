import datetime
import operator
from collections import OrderedDict
from enum import Enum
from functools import reduce
from typing import Iterable, List, Optional, Set, Type

from core.logic.dates import date_range_from_params, month_end, parse_month
from core.logic.serialization import parse_b64json
from core.logic.type_conversion import to_bool
from django.conf import settings
from django.core.exceptions import EmptyResultSet
from django.db.models import (
    Case,
    DateField,
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
from logs.models import AccessLog, Dimension, DimensionText, ReportType


class FlexibleDataSlicer:
    implicit_dims = ["date", "platform", "metric", "organization", "target", "report_type"]
    COL_BASE = "base"
    COL_COMPARED = "compared"
    COL_DIFF = "diff"
    COL_REL_DIFF = "reldiff"
    COL_TOTAL = "_total"
    MAXIMUM_POSSIBLE_GROUPS = 100
    MAXIMUM_POSSIBLE_PARTS = 1000

    TREND_MODE_COLS = (COL_BASE, COL_COMPARED, COL_DIFF, COL_REL_DIFF)

    def __init__(
        self,
        primary_dimension,
        *,
        tag_roll_up=False,
        include_all_zero_rows=False,
        include_row_totals=False,
        include_col_totals=False,
        trend_mode=False,
        base_subset_filters: Optional[List[DimensionFilter]] = None,
        compared_subset_filters: Optional[List[DimensionFilter]] = None,
        use_clickhouse=None,
    ):
        """
        :param primary_dimension: The dimension that will be used to group the results into rows.
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
        :param use_clickhouse: whether to use ClickHouse for queries where it is supported
        """
        self.use_clickhouse = (
            settings.CLICKHOUSE_QUERY_ACTIVE if use_clickhouse is None else use_clickhouse
        )
        self.primary_dimension = primary_dimension
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
            "primary_dimension": self.primary_dimension,
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
        }

    @property
    def filters(self) -> dict:
        return self.create_filters()

    def create_filters(self, ignore_dimensions=None, use_clickhouse=False):
        if ignore_dimensions:
            if type(ignore_dimensions) in (list, tuple, set):
                ignore_dimensions = set(ignore_dimensions)
            else:
                ignore_dimensions = {ignore_dimensions}
        else:
            ignore_dimensions = set()
        ret = {}
        for df in self.dimension_filters:
            if df.dimension not in ignore_dimensions or isinstance(df, TagDimensionFilter):
                # tag filters are not ignored even if they are for an ignored dimension
                ret.update(df.query_params(clickhouse_compatible=use_clickhouse))
        logger.debug("filters: %s", ret)
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
        return ret

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

    def _validate_dim_compatible_with_all_rts(self, dim_name: str, rts: List[ReportType]):
        dims = {e.dimension_by_attr_name(dim_name) for e in rts}
        if len(dims) > 1:
            raise SlicerConfigError(
                "It is not possible to group by explicit dimension unless that "
                "dimension is exactly the same for all selected report types",
                SlicerConfigErrorCode.E100,
            )

    def check_params(self):
        """
        Checks that the config makes sense and data could be retrieved
        """
        rt_filter = []
        for fltr in self.dimension_filters:
            if isinstance(fltr, ForeignKeyDimensionFilter) and fltr.dimension == "report_type":
                rt_filter = fltr.values
        if len(rt_filter) != 1:
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

        if self.trend_mode:
            if not self.base_subset_filters or not self.compared_subset_filters:
                raise SlicerConfigError(
                    "Both base and compared subset filters must be specified when trend_mode is "
                    "True",
                    SlicerConfigErrorCode.E111,
                )

    def check_params_for_data_query(self):
        """
        Extra checks to be performed before data query is run. These do not apply to other
        functions, such as getting possible dimension values.
        """
        if not self.group_by and not self.trend_mode:
            raise SlicerConfigError(
                'At least one "group" dimension must be given to define the output columns',
                SlicerConfigErrorCode.E106,
            )

    def get_queryset(self, part: Optional[list] = None):
        self.check_params()
        self.check_params_for_data_query()
        self.check_part(part)

        filters = {**self.filters}
        if part:
            for dim, value in zip(self.split_by, part):
                fltr = self.filter_instance(dim, value)
                filters.update(fltr.query_params())

        field, modifier = AccessLog.get_dimension_field(self.primary_dimension)
        if isinstance(field, ForeignKey):
            primary_cls = field.remote_field.model
            if self.tag_roll_up:
                # we will be summing up by tag, so the query is a bit different
                # (slightly similar to mapped primary dimension)
                tag_scope = TagClass.tag_scope_from_target_class(primary_cls)
                target_attr = Tag.target_attr_from_scope(tag_scope)
                tag_filters = [self.tag_filter] if self.tag_filter else []
                if self.tag_class:
                    tag_filters.append(Q(tag_class_id=self.tag_class))
                # if we apply the tag filter on the qs itself, it for some reason creates
                # an extremely slow query (at least on K1), maybe because joins with organization
                # created for organization specific tags
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
                            f"{target_attr}__accesslog",
                            condition=Q(
                                **extend_query_filter(filters, f"{target_attr}__accesslog__")
                            ),
                        )
                    )
                    .values("pk")
                    .annotate(**self._prepare_annotations())
                )
            elif (self.include_all_zero_rows and not self.trend_mode) or self.primary_dimension in [
                ob.lstrip("-").split("__")[0] for ob in self.order_by
            ]:
                # we need to put the primary dimension model into play because zero usage is
                # requested, or we are sorting by the primary dimension
                qs = primary_cls.objects.all()
                if primary_cls is Organization and self.organization_filter is not None:
                    qs = qs.filter(pk__in=self.organization_filter)
                qs = (
                    qs.filter(**self._primary_dimension_filter())
                    .annotate(
                        relevant_accesslogs=FilteredRelation(
                            "accesslog", condition=Q(**extend_query_filter(filters, "accesslog__"))
                        )
                    )
                    .values("pk")
                    .annotate(**self._prepare_annotations())
                )
                self._primary_dimension_query = True
            else:
                # zero usage is not needed - we can just aggregate the accesslogs, which can be
                # much faster
                # if report_type is primary dimension and we use materialized reports,
                # we need to remap the report type id back to the original one
                pk_def = F(self.primary_dimension)
                if self.primary_dimension == "report_type" and self._mat_reports_map:
                    whens = [
                        When(then=Value(orig), **{self.primary_dimension: pk})
                        for pk, orig in self._mat_reports_map.items()
                    ]
                    pk_def = Case(*whens, default=pk_def, output_field=IntegerField())

                qs = (
                    AccessLog.objects.filter(**filters)
                    .annotate(pk=pk_def)
                    .values("pk")
                    .distinct()
                    .annotate(**self._prepare_annotations(accesslog_prefix=""))
                )
        elif field and self.primary_dimension.startswith("dim"):
            qs = (
                AccessLog.objects.filter(**filters)
                .values(self.primary_dimension)
                .distinct()
                .annotate(**self._prepare_annotations(accesslog_prefix=""))
            )
        elif field and isinstance(field, DateField):
            if modifier and modifier != "year":
                raise ValueError('The only modifier allowed for date is "year", i.e. date__year')
            qs = (
                AccessLog.objects.filter(**filters)
                .values(self.primary_dimension)
                .distinct()
                .annotate(**self._prepare_annotations(accesslog_prefix=""))
            )
        elif field:
            raise SlicerConfigError(
                f"Primary dimension {self.primary_dimension} is not supported",
                SlicerConfigErrorCode.E102,
                details={"dimension": self.primary_dimension},
            )
        else:
            raise SlicerConfigError(
                f"Primary dimension {self.primary_dimension} is not valid",
                SlicerConfigErrorCode.E103,
                details={"dimension": self.primary_dimension},
            )
        if not self.include_all_zero_rows:
            # total is added in _prepare_annotations and is a sum of all the value columns
            qs = qs.filter(_total__gt=0)
        elif self.trend_mode:
            # in trend mode, we need to filter out rows where both base and compared are zero
            # even if include_all_zero_rows is True
            qs = qs.exclude(base=0, compared=0)
        return qs

    def _primary_dimension_filter(self) -> dict:
        ret = {}
        for df in self.dimension_filters:
            if df.dimension == self.primary_dimension:
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
            if gb_query.count() > self.MAXIMUM_POSSIBLE_GROUPS:
                raise SlicerConfigError(
                    f"There are too many ({gb_query.count()}) possible groups, please refine "
                    f"you configuration",
                    SlicerConfigErrorCode.E101,
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
            raise SlicerConfigError(
                "The requested dimension is not supported", SlicerConfigErrorCode.E107
            )
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
            raise SlicerConfigError(
                "The requested dimension is not supported", SlicerConfigErrorCode.E107
            )
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
        query_params = self.create_filters(
            ignore_dimensions=ignore_dimensions, use_clickhouse=use_clickhouse
        )
        if use_clickhouse:
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
            query = AccessLog.objects.filter(**query_params).values(*dimensions).distinct()

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
        for ob in self.order_by:
            prefix = "-" if ob.startswith("-") else ""
            ob = ob.lstrip("-")
            if ob == "tag" and self.tag_roll_up:
                obs.append(prefix + "name")
            elif ob.startswith("dim"):
                # when sorting by dimX we need to map the IDs to the corresponding texts
                # because the mapping does not use a Foreign key relationship, we use a subquery
                dt_query = DimensionText.objects.filter(id=OuterRef(ob)).values("text")[:1]
                qs = qs.annotate(**{ob + "sort": Subquery(dt_query)})
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
                ob == self.primary_dimension and not ob.startswith("date") and not self.tag_roll_up
            ):
                if ob == "target":
                    # title does not have `short_name`, just `name`
                    obs.append(prefix + "name")
                else:
                    # if there is a name, we want name, if not, we want short_name
                    # the following simulates this
                    qs = qs.annotate(sort_name=Concat(F(f"name_{lang}"), F("short_name")))
                    obs.append(prefix + "sort_name")
            elif ob.startswith(self.primary_dimension) and not self.tag_roll_up:
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

        field, modifier = AccessLog.get_dimension_field(self.primary_dimension)
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
                filters = {**self.filters}
                if self.split_by and part:
                    for dim, value in zip(self.split_by, part):
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
                            "accesslog", condition=Q(**extend_query_filter(filters, "accesslog__"))
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
                raise SlicerConfigError(
                    code=SlicerConfigErrorCode.E108,
                    message="`part` argument must be given when `split_by` is used",
                )
            if len(self.split_by) != len(part):
                raise SlicerConfigError(
                    "The `part` value must be the same length as `split_by`",
                    code=SlicerConfigErrorCode.E109,
                    details={"split_by": self.split_by, "part": part},
                )
        elif part:
            # part cannot be used if `split_by` is not set up
            raise SlicerConfigError(
                code=SlicerConfigErrorCode.E110,
                message="`split_by` must be set up when `part` argument is given",
            )

    def resolve_explicit_dimension(self, dim_ref: str) -> Optional[Dimension]:
        rts = self.involved_report_types()
        if rts:
            # the dimension should be common to all report types
            # but we want to ensure that
            dims = {rt.dimension_by_attr_name(dim_ref) for rt in rts}
            if len(dims) > 1:
                raise SlicerConfigError(
                    code=SlicerConfigErrorCode.E113,
                    message="Dimension is not common to all used report types",
                )
            return dims.pop()
        return None

    def involved_report_types(self) -> List[ReportType]:
        """
        Returns a list of report types that are part of the query if there is any filter on them.
        If there is no filter, None is returned.
        """
        query_params = {}
        for fltr in self.dimension_filters:
            if fltr.dimension == "report_type":
                query_params = fltr.query_params(primary_filter=True)
                break
        if query_params:
            return list(ReportType.objects.filter(**query_params))
        return list(ReportType.objects.exclude_materialized())

    def _replace_report_type_with_materialized(
        self, extra_dimensions_to_preserve=None, ignore_primary=False
    ):
        rts = self.involved_report_types()
        for rt in rts:
            dimensions = {fltr.dimension for fltr in self.dimension_filters}
            if not ignore_primary:
                dimensions.add(self.primary_dimension)
            dimensions |= {dim.lstrip("-") for dim in self.order_by}
            dimensions |= set(self.group_by)
            dimensions |= set(self.split_by)
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
        if not (primary_dimension := params.get("primary_dimension")):
            raise SlicerConfigError(
                '"primary_dimension" key must be present', SlicerConfigErrorCode.E104
            )
        slicer = cls(primary_dimension)
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
                if filters := params.get(params_name):
                    filters = parse_b64json(filters)
                    if "date" in filters:
                        return [cls.filter_instance("date", filters["date"])]

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
        return slicer

    @classmethod
    def create_from_config(cls, params: dict) -> "FlexibleDataSlicer":
        """
        Takes the output of self.config() and converts it into a slicer instance
        """
        primary_dimension = params.get("primary_dimension")
        if not primary_dimension:
            raise SlicerConfigError(
                '"primary_dimension" key must be present', SlicerConfigErrorCode.E104
            )
        slicer = cls(primary_dimension)
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

        if self.trend_mode:
            # in trend mode, we need to calculate coverage for both base and compared periods
            # separately
            def subset_filters(fltrs):
                for fltr in fltrs:
                    if isinstance(fltr, DateDimensionFilter):
                        return {"start_month": fltr.start, "end_month": fltr.end}
                return {}

            base_range = subset_filters(self.base_subset_filters)
            base_cov = self._get_coverage_for_filters(**base_range, **coverage_filters)
            compared_range = subset_filters(self.compared_subset_filters)
            compared_cov = self._get_coverage_for_filters(**compared_range, **coverage_filters)
            return {"base": base_cov, "compared": compared_cov}
        else:
            cov = self._get_coverage_for_filters(**coverage_filters)
            return {"overall": cov}


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

    def __str__(self):
        return self.value


class SlicerConfigError(Exception):
    """
    E100: It is not possible to group by explicit dimension unless exactly one report
          type is selected by a filter
    E101: There are too many possible groups, please refine you configuration,
    E102: The specified primary dimension is not supported.
    E103: The specified primary dimension is not valid.
    E104: The attribute 'primary_dimension' must be present in the request.
    E105: The attribute 'dimension' must be present in the request.
    E106: At least one dimension must be selected to define the output columns.
    E107: The queried dimension is not supported.
    E108: Part is not specified and `split_by` is used.
    E109: Part specification is incompatible with `split_by`.
    E110: Part was specified without `split_by` being active.
    E111: Only date filters are supported for subsets in trend mode.
    E112: There are too many possible parts, please refine you configuration.
    E113: Dimension is not common to all used report types.
    """

    def __init__(self, message, code: SlicerConfigErrorCode, *args, details=None, **kwargs):
        self.message = message
        self.code = code.value
        self.details = details
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"SlicerConfigError {self.code}: {self.message}"
