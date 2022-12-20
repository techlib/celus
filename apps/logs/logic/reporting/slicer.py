import datetime
import operator
from collections import OrderedDict
from enum import Enum
from functools import reduce
from typing import Iterable, List, Optional, Type

from core.logic.dates import date_range_from_params, month_end, parse_month
from core.logic.serialization import parse_b64json
from core.logic.type_conversion import to_bool
from django.conf import settings
from django.core.exceptions import EmptyResultSet
from django.db.models import (
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
)
from django.db.models.functions import Coalesce, Concat
from hcube.api.models.aggregation import Sum as HSum
from logs.cubes import AccessLogCube, ch_backend
from logs.logic.queries import find_best_materialized_view, logger
from logs.logic.reporting.filters import (
    CLICKHOUSE_ID_COUNT_LIMIT,
    ClickhouseIncompatibleFilter,
    DateDimensionFilter,
    DimensionFilter,
    ExplicitDimensionFilter,
    ForeignKeyDimensionFilter,
    TagDimensionFilter,
)
from logs.models import AccessLog, DimensionText, ReportType
from organizations.logic.queries import extend_query_filter
from organizations.models import Organization
from tags.models import Tag, TagClass


class FlexibleDataSlicer:
    implicit_dims = ['date', 'platform', 'metric', 'organization', 'target', 'report_type']

    def __init__(
        self, primary_dimension, tag_roll_up=False, include_all_zero_rows=False, use_clickhouse=None
    ):
        self.use_clickhouse = (
            settings.CLICKHOUSE_QUERY_ACTIVE if use_clickhouse is None else use_clickhouse
        )
        self.primary_dimension = primary_dimension
        self.dimension_filters: List[DimensionFilter] = []
        self.group_by = []
        self.order_by = []
        self.split_by = []
        self._annotations = []
        self.organization_filter = None
        self.include_all_zero_rows = include_all_zero_rows
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

    def config(self):
        return {
            "primary_dimension": self.primary_dimension,
            "filters": [fltr.config() for fltr in self.dimension_filters],
            "group_by": self.group_by,
            "order_by": self.order_by,
            "zero_rows": self.include_all_zero_rows,
            "split_by": self.split_by,
            "tag_roll_up": self.tag_roll_up,
            "tag_class": self.tag_class,
            "show_untagged_remainder": self.show_untagged_remainder,
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
        logger.info('filters: %s', ret)
        if self.organization_filter is not None:
            # convert organization filter to a list of ids for easier compatibility with
            # clickhouse and for simpler query (even though that is not a big deal)
            if type(self.organization_filter) in (list, tuple, set):
                org_filter_pks = self.organization_filter
            else:
                org_filter_pks = set(self.organization_filter.values_list('pk', flat=True))
            if 'organization_id__in' in ret:
                orig_orgs = set(ret['organization_id__in'])
                ret['organization_id__in'] = list(orig_orgs & org_filter_pks)
            else:
                ret['organization_id__in'] = list(org_filter_pks)
        logger.info('filters with org: %s', ret)
        return ret

    def add_extra_organization_filter(self, org_filter: Iterable):
        self.organization_filter = org_filter

    def add_filter(self, dimension_filter: DimensionFilter, add_group=False):
        self.dimension_filters.append(dimension_filter)
        if add_group:
            self.group_by.append(dimension_filter.dimension)

    def add_group_by(self, dimension):
        self.group_by.append(dimension)

    def add_split_by(self, dimension):
        self.split_by.append(dimension)

    def check_params(self):
        """
        Checks that the config makes sense and data could be retrieved
        """
        has_explicit_dim_group_by = False
        for dim_name in self.group_by:
            if dim_name.startswith('dim'):
                has_explicit_dim_group_by = True
                break
        rt_filter = self.filters.get('report_type_id__in', [])
        if has_explicit_dim_group_by and len(rt_filter) != 1:
            raise SlicerConfigError(
                'It is not possible to group by explicit dimension unless exactly one report '
                'type is selected by a filter',
                SlicerConfigErrorCode.E100,
            )

    def check_params_for_data_query(self):
        """
        Extra checks to be performed before data query is run. These do not apply to other functions,
        such as getting possible dimension values.
        """
        if not self.group_by:
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
                tag_ids = Tag.objects.filter(tag_class__scope=tag_scope, *tag_filters).values_list(
                    'pk', flat=True
                )
                qs = (
                    Tag.objects.filter(pk__in=tag_ids)
                    .annotate(
                        relevant_accesslogs=FilteredRelation(
                            f'{target_attr}__accesslog',
                            condition=Q(
                                **extend_query_filter(filters, f'{target_attr}__accesslog__')
                            ),
                        )
                    )
                    .values('pk')
                    .annotate(**self._prepare_annotations())
                )
            elif self.include_all_zero_rows or self.primary_dimension in [
                ob.lstrip('-').split('__')[0] for ob in self.order_by
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
                            'accesslog', condition=Q(**extend_query_filter(filters, 'accesslog__'))
                        )
                    )
                    .values('pk')
                    .annotate(**self._prepare_annotations())
                )
                self._primary_dimension_query = True
            else:
                # zero usage is not needed - we can just aggregate the accesslogs, which can be
                # much faster
                qs = (
                    AccessLog.objects.filter(**filters)
                    .annotate(pk=F(self.primary_dimension))
                    .values('pk')
                    .distinct()
                    .annotate(**self._prepare_annotations(accesslog_prefix=''))
                )
        elif field and self.primary_dimension.startswith('dim'):
            qs = (
                AccessLog.objects.filter(**filters)
                .values(self.primary_dimension)
                .distinct()
                .annotate(**self._prepare_annotations(accesslog_prefix=''))
            )
        elif field and isinstance(field, DateField):
            if modifier and modifier != 'year':
                raise ValueError('The only modifier allowed for date is "year", i.e. date__year')
            qs = (
                AccessLog.objects.filter(**filters)
                .values(self.primary_dimension)
                .distinct()
                .annotate(**self._prepare_annotations(accesslog_prefix=''))
            )
        elif field:
            raise SlicerConfigError(
                f'Primary dimension {self.primary_dimension} is not supported',
                SlicerConfigErrorCode.E102,
                details={'dimension': self.primary_dimension},
            )
        else:
            raise SlicerConfigError(
                f'Primary dimension {self.primary_dimension} is not valid',
                SlicerConfigErrorCode.E103,
                details={'dimension': self.primary_dimension},
            )
        if not self.include_all_zero_rows:
            # total is added in _prepare_annotations and is a sum of all the value columns
            qs = qs.filter(_total__gt=0)
        return qs

    def _primary_dimension_filter(self) -> dict:
        ret = {}
        for df in self.dimension_filters:
            if df.dimension == self.primary_dimension:
                ret.update(df.query_params(primary_filter=True))
        return ret

    def _prepare_annotations(
        self, max_number=100, accesslog_prefix='relevant_accesslogs__'
    ) -> dict:
        gb_query = self.get_possible_groups_queryset()
        if not gb_query:
            return {
                'total': Coalesce(Sum(f'{accesslog_prefix}value'), 0),
                '_total': Coalesce(Sum(f'{accesslog_prefix}value'), 0),
            }
        if gb_query.count() > max_number:
            raise SlicerConfigError(
                f'There are too many ({gb_query.count()}) possible groups, please refine '
                f'you configuration',
                SlicerConfigErrorCode.E101,
                details={'group_count': gb_query.count()},
            )
        if gb_query.count() == 0:
            return {}
        # we have some group_by values, but not too many
        annotations = {}
        for group in gb_query:
            key = self._group_dict_to_group_key(group)
            filters = {f'{accesslog_prefix}{dim}': group[dim] for dim in self.group_by}
            annotations[key] = Coalesce(Sum(f'{accesslog_prefix}value', filter=Q(**filters)), 0)
            annotations['_total'] = Coalesce(Sum(f'{accesslog_prefix}value'), 0)
        self._annotations = annotations
        return annotations

    def _group_dict_to_group_key(self, group: dict) -> str:
        keys = [group[dim] for dim in self.group_by]
        return 'grp-' + ','.join(map(str, keys))

    def decode_key(self, key: str) -> dict:
        if not key.startswith('grp-'):
            raise ValueError('Key must start with "grp-"')
        # 'None' can happen if we group by dimension that is not used and thus has no values
        # present
        pks = [None if x == 'None' else (int(x) if '-' not in x else x) for x in key[4:].split(',')]
        return OrderedDict([(dim, pks[i]) for (i, dim) in enumerate(self.group_by)])

    @classmethod
    def _text_to_filter(cls, text, text_fields=('name',)):
        return reduce(
            operator.or_, (Q(**{f'{text_field}__ilike': text}) for text_field in text_fields)
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
                'pk', flat=True
            )
            if clickhouse_compatible:
                if subfilter.count() > CLICKHOUSE_ID_COUNT_LIMIT:
                    raise ClickhouseIncompatibleFilter('Too many ids to resolve')
                subfilter = list(subfilter)
            extra_filter = {f'{dimension}_id__in': subfilter}
        elif field and dimension.startswith('dim'):
            subfilter = DimensionText.objects.filter(
                self._text_to_filter(text_filter, text_fields=('text', 'text_local'))
            ).values_list('pk', flat=True)
            if clickhouse_compatible:
                if subfilter.count() > CLICKHOUSE_ID_COUNT_LIMIT:
                    raise ClickhouseIncompatibleFilter('Too many ids to resolve')
                subfilter = list(subfilter)
            extra_filter = {f'{dimension}__in': subfilter}
        else:
            raise SlicerConfigError(
                'The requested dimension is not supported', SlicerConfigErrorCode.E107
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
            extra_filter = {f'{dimension}_id__in': pks}
        elif field and dimension.startswith('dim'):
            extra_filter = {f'{dimension}__in': pks}
        else:
            raise SlicerConfigError(
                'The requested dimension is not supported', SlicerConfigErrorCode.E107
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
            {(k if k != f'{dimension}_id' else dimension): v for k, v in rec._asdict().items()}
            for rec in result
        ]
        return {'count': count, 'values': data, 'cropped': cropped}

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
            logger.debug('Query: %s', query.query)
        except EmptyResultSet:
            logger.debug('Query: EmptyResultSet')
        count = query.count()
        cropped = False
        if max_values_count and count > max_values_count:
            cropped = True
            query = query.annotate(score=Coalesce(Sum('value'), 0)).order_by('-score')
            query = query[:max_values_count]
        return {'count': count, 'values': list(query), 'cropped': cropped}

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
                f'{dim}_id' if f'{dim}_id' in AccessLogCube._dimensions else dim
                for dim in dimensions
            ]
            query = (
                AccessLogCube.query()
                .filter(**query_params)
                .group_by(*dims)
                .aggregate(score=HSum('value'))
                .order_by('-score')
            )
            return query
        else:
            # check if we could use a materialized rt
            if len(rt_fltr := query_params.get('report_type_id__in', [])) == 1:
                # we can only use it if there is one RT
                rt = ReportType.objects.get(pk=rt_fltr[0])
                used_dimensions = {
                    dim.split('__')[0] for dim in query_params.keys() if dim != 'report_type_id__in'
                }
                used_dimensions = [
                    dim[:-3] if dim.endswith('_id') else dim for dim in used_dimensions
                ]
                new_rt = find_best_materialized_view(rt, used_dimensions)
                if new_rt:
                    query_params['report_type_id__in'] = [new_rt.pk]
            query = AccessLog.objects.filter(**query_params).values(*dimensions).distinct()
            return query

    def get_possible_groups_queryset(self):
        if self.group_by:
            return self.get_possible_dimension_values_queryset(self.group_by)
        return None

    def get_parts_queryset(self):
        if self.split_by:
            return self.get_possible_dimension_values_queryset(self.split_by)
        return None

    def get_data(self, lang='en', part: Optional[list] = None) -> QuerySet[dict]:
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
            prefix = '-' if ob.startswith('-') else ''
            ob = ob.lstrip('-')
            dealt_with = False
            if ob == 'tag' and self.tag_roll_up:
                dealt_with = True
                obs.append(prefix + 'name')
            if ob.startswith('dim'):
                # when sorting by dimX we need to map the IDs to the corresponding texts
                # because the mapping does not use a Foreign key relationship, we use a subquery
                dt_query = DimensionText.objects.filter(id=OuterRef(ob)).values('text')[:1]
                qs = qs.annotate(**{ob + 'sort': Subquery(dt_query)})
                obs.append(prefix + ob + 'sort')
                dealt_with = True
            elif ob.startswith('grp-'):
                if ob not in self._annotations:
                    # we ignore sort groups that are not in the data
                    logger.debug('Ignoring unknown order by "%s"', ob)
                    dealt_with = True
                else:
                    obs.append(prefix + ob)
                    dealt_with = True
            elif ob == self.primary_dimension and not ob.startswith('date'):
                if ob == 'target':
                    # title does not have `short_name`, just `name`
                    obs.append(prefix + 'name')
                else:
                    # if there is a name, we want name, if not, we want short_name
                    # the following simulates this
                    qs = qs.annotate(sort_name=Concat(F(f'name_{lang}'), F('short_name')))
                    obs.append(prefix + 'sort_name')
                dealt_with = True
            elif ob.startswith(self.primary_dimension):
                if self._primary_dimension_query:
                    # we are querying the related model, not accesslog, we need to process the
                    # order by definition
                    start, *rest, end = ob.split('__')
                    obs.append(prefix + end)
                else:
                    # we do not validate this, so it could be a problem, but it would crash rather
                    # than produce wrong results, so we leave it as is
                    obs.append(prefix + ob)
                dealt_with = True
            if not dealt_with:
                # this means that the order by is not consistent with the rest of the query
                # it would be prudent to raise an error, but there are already existing data
                # which have this problem, so we just ignore it and drop the ordering
                logger.error('Dropping inconsistent order by "%s"', ob)
        qs = qs.order_by(*obs)
        try:
            logger.debug('Slicer query: %s', qs.query)
        except EmptyResultSet:
            logger.debug('Slicer query: empty')
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
                    tags__in=Tag.objects.filter(tag_class__scope=tag_scope.value, *tag_filters)
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
                return (
                    qs.filter(**self._primary_dimension_filter())
                    .annotate(
                        relevant_accesslogs=FilteredRelation(
                            'accesslog', condition=Q(**extend_query_filter(filters, 'accesslog__'))
                        )
                    )
                    .values('pk')
                    .aggregate(**self._prepare_annotations())
                )
            raise ValueError('Remainder can only be computed when `tag_roll_up` is active')
        # the following will happen if the primary dimension is not a foreign key
        # and thus cannot be one of the taggable models (Organization, Platform, Title)
        raise ValueError('Remainder can only be computed when primary dimension supports tags')

    def check_part(self, part):
        """
        Checks that the `split_by` definition is compatible with the part value given
        """
        if self.split_by:
            if not part:
                raise SlicerConfigError(
                    code=SlicerConfigErrorCode.E108,
                    message='`part` argument must be given when `split_by` is used',
                )
            if len(self.split_by) != len(part):
                raise SlicerConfigError(
                    'The `part` value must be the same length as `split_by`',
                    code=SlicerConfigErrorCode.E109,
                    details={'split_by': self.split_by, 'part': part},
                )
        elif part:
            # part cannot be used if `split_by` is not set up
            raise SlicerConfigError(
                code=SlicerConfigErrorCode.E110,
                message='`split_by` must be set up when `part` argument is given',
            )

    def resolve_explicit_dimension(self, dim_ref: str):
        rts = self.involved_report_types()
        if rts and len(rts) == 1:
            return rts[0].dimension_by_attr_name(dim_ref)
        return None

    def involved_report_types(self) -> [ReportType]:
        """
        Returns a list of report types that are part of the query if there is any filter on them.
        If there is no filter, None is returned.
        """
        query_params = {}
        for fltr in self.dimension_filters:
            if fltr.dimension == 'report_type':
                query_params = fltr.query_params(primary_filter=True)
                break
        if query_params:
            return list(ReportType.objects.filter(**query_params))
        return list(ReportType.objects.filter(materialization_spec__isnull=True))

    def _replace_report_type_with_materialized(
        self, extra_dimensions_to_preserve=None, ignore_primary=False
    ):
        rts = self.involved_report_types()
        for rt in rts:
            dimensions = {fltr.dimension for fltr in self.dimension_filters}
            if not ignore_primary:
                dimensions.add(self.primary_dimension)
            dimensions |= {dim.lstrip('-') for dim in self.order_by}
            dimensions |= set(self.group_by)
            if extra_dimensions_to_preserve:
                dimensions |= set(extra_dimensions_to_preserve)
            materialized_report = find_best_materialized_view(rt, dimensions)
            if materialized_report:
                logger.info('Using materialized report: %s instead of %s', materialized_report, rt)
                for fltr in self.dimension_filters:
                    if fltr.dimension == 'report_type':
                        fltr.values = [
                            materialized_report.pk if rt.pk == val else val for val in fltr.values
                        ]

    @classmethod
    def filter_class(cls, dimension) -> Type[DimensionFilter]:
        """
        Finds the right Filter class for the dimension at hand
        """
        if dimension.startswith('tag__'):
            return TagDimensionFilter
        field, _modifier = AccessLog.get_dimension_field(dimension)
        if isinstance(field, ForeignKey):
            return ForeignKeyDimensionFilter
        elif isinstance(field, DateField):
            return DateDimensionFilter
        elif isinstance(field, IntegerField):
            return ExplicitDimensionFilter
        else:
            raise ValueError(f'not supported yet ({dimension}, {field}, {_modifier})')

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
                return filter_class(field.name, value, value)
            if type(value) is int:
                # we treat int in a special way as the whole year with that number
                value = {'start': f'{value}-01-01', 'end': f'{value}-12-31'}
            elif type(value) is str:
                start = parse_month(value)
                end = month_end(start)
                value = {'start': start, 'end': end}
            return filter_class(field.name, *date_range_from_params(value))
        elif filter_class is TagDimensionFilter:
            dimension = dimension[len('tag__') :]
            return filter_class(dimension, value)
        else:
            return filter_class(dimension, value)

    @classmethod
    def create_from_params(cls, params: dict) -> 'FlexibleDataSlicer':
        """
        Takes the parameters as they would be obtained from the API and creates a new slicer
        instance based on those.
        """
        if not (primary_dimension := params.get('primary_dimension')):
            raise SlicerConfigError(
                '"primary_dimension" key must be present', SlicerConfigErrorCode.E104
            )
        slicer = cls(primary_dimension)
        # filters
        filters = params.get('filters')
        filters = parse_b64json(filters) if filters else {}
        for key, value in filters.items():
            slicer.add_filter(cls.filter_instance(key, value))
        # groups
        groups = params.get('groups')
        groups = parse_b64json(groups) if groups else []
        for group in groups:
            slicer.add_group_by(group)
        # split by
        splits = params.get('split_by')
        splits = parse_b64json(splits) if splits else []
        for split in splits:
            slicer.add_split_by(split)
        # ordering
        if order_by := params.get('order_by'):
            slicer.order_by = [order_by]
        # extra stuff
        # the zero_rows value should be recoded to python bool, but we want to make sure
        slicer.include_all_zero_rows = to_bool(params.get('zero_rows', ''))
        slicer.tag_roll_up = to_bool(params.get('tag_roll_up', ''))
        slicer.tag_class = params.get('tag_class')
        slicer.show_untagged_remainder = to_bool(params.get('show_untagged_remainder', ''))
        return slicer

    @classmethod
    def create_from_config(cls, params: dict) -> 'FlexibleDataSlicer':
        """
        Takes the output of self.config() and converts it into a slicer instance
        """
        primary_dimension = params.get('primary_dimension')
        if not primary_dimension:
            raise SlicerConfigError(
                '"primary_dimension" key must be present', SlicerConfigErrorCode.E104
            )
        slicer = cls(primary_dimension)
        # filters
        filters = params.get('filters', [])
        for fltr in filters:
            dim = fltr['dimension']
            if 'tag_ids' in fltr:
                dim_filter = TagDimensionFilter(dim, fltr['tag_ids'])
            else:
                filter_class = cls.filter_class(dim)
                if filter_class is DateDimensionFilter:
                    dim_filter = filter_class(dim, fltr['start'], fltr['end'])
                else:
                    dim_filter = filter_class(dim, fltr['values'])
            slicer.add_filter(dim_filter)
        # groups
        slicer.group_by = params.get('group_by', [])
        # split by
        slicer.split_by = params.get('split_by', [])
        # ordering
        slicer.order_by = params.get('order_by', [])
        # extra stuff
        slicer.include_all_zero_rows = params.get('zero_rows', False)
        slicer.tag_roll_up = params.get('tag_roll_up', False)
        slicer.tag_class = params.get('tag_class')
        slicer.show_untagged_remainder = params.get('show_untagged_remainder', False)
        return slicer

    def filter_to_str(self, fltr):
        """
        For some filters, we need context of the slicer to be able to serialize it
        :param fltr:
        :return:
        """
        if isinstance(fltr, ExplicitDimensionFilter):
            dim = self.resolve_explicit_dimension(fltr.dimension)
            return f'{dim.short_name}: {fltr.value_str}'
        elif isinstance(fltr, ForeignKeyDimensionFilter):
            field, _modifier = AccessLog.get_dimension_field(fltr.dimension)
            return f'{field.remote_field.model._meta.verbose_name}: {fltr.value_str}'
        elif isinstance(fltr, DateDimensionFilter):
            field, _modifier = AccessLog.get_dimension_field(fltr.dimension)
            return f'{field.verbose_name}: {fltr.value_str}'
        elif isinstance(fltr, TagDimensionFilter):
            return f'{fltr.dimension}: {fltr.value_str}'
        raise NotImplementedError(f'Unsupported filter class: {fltr.__class__.__name__}')


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
    """

    def __init__(self, message, code: SlicerConfigErrorCode, *args, details=None, **kwargs):
        self.message = message
        self.code = code.value
        self.details = details
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f'SlicerConfigError {self.code}: {self.message}'
