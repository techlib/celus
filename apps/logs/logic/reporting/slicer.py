import datetime
import operator
from collections import OrderedDict
from enum import Enum
from functools import reduce
from typing import List, Iterable, Optional, Tuple, Type

from django.core.exceptions import FieldDoesNotExist
from django.db.models import (
    ForeignKey,
    FilteredRelation,
    Q,
    DateField,
    Sum,
    Field,
    CharField,
    OuterRef,
    Subquery,
    F,
    IntegerField,
)
from django.db.models.functions import Coalesce, Cast, Concat

from core.logic.dates import parse_month, month_end, date_range_from_params
from core.logic.serialization import parse_b64json
from logs.logic.queries import logger, find_best_materialized_view
from logs.logic.reporting.filters import (
    DimensionFilter,
    DateDimensionFilter,
    ForeignKeyDimensionFilter,
    ExplicitDimensionFilter,
)
from logs.models import AccessLog, Dimension, DimensionText, ReportType
from organizations.logic.queries import extend_query_filter
from organizations.models import Organization


class FlexibleDataSlicer:
    implicit_dims = ['date', 'platform', 'metric', 'organization', 'target', 'report_type']

    def __init__(self, primary_dimension):
        self.primary_dimension = primary_dimension
        self.dimension_filters: List[DimensionFilter] = []
        self.group_by = []
        self.order_by = []
        self.split_by = []
        self._annotations = []
        self.organization_filter = None
        self.include_all_zero_rows = False

    def config(self):
        return {
            "primary_dimension": self.primary_dimension,
            "filters": [fltr.config() for fltr in self.dimension_filters],
            "group_by": self.group_by,
            "order_by": self.order_by,
            "zero_rows": self.include_all_zero_rows,
            "split_by": self.split_by,
        }

    @property
    def filters(self) -> dict:
        return self.create_filters()

    def create_filters(self, ignore_dimensions=None):
        if ignore_dimensions:
            if type(ignore_dimensions) in (list, tuple, set):
                ignore_dimensions = set(ignore_dimensions)
            else:
                ignore_dimensions = {ignore_dimensions}
        else:
            ignore_dimensions = set()
        ret = {}
        for df in self.dimension_filters:
            if df.dimension not in ignore_dimensions:
                ret.update(df.query_params())
        if self.organization_filter is not None:
            ret['organization__in'] = self.organization_filter
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

    def accesslog_queryset(self, ignore_dimensions=None):
        self.check_params()
        query_params = self.create_filters(ignore_dimensions=ignore_dimensions)
        return AccessLog.objects.filter(**query_params)

    def get_queryset(self, part: Optional[list] = None):
        self.check_params()
        self.check_params_for_data_query()
        filters = {**self.filters}

        # handle part and split_by
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
            for dim, value in zip(self.split_by, part):
                fltr = self.filter_instance(dim, value)
                filters.update(fltr.query_params())

        field, modifier = AccessLog.get_dimension_field(self.primary_dimension)
        if isinstance(field, ForeignKey):
            primary_cls = field.remote_field.model
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

    def create_text_filter(self, dimension, text_filter) -> (dict, dict):
        """
        Creates a dict that can be used in queryset filter to filter only those instances of
        `dimension` which contain the text from `text_filter`.
        """
        field, modifier = AccessLog.get_dimension_field(dimension)
        extra_annot = {}
        if isinstance(field, ForeignKey):
            primary_cls = field.remote_field.model
            subfilter = primary_cls.objects.filter(self._text_to_filter(text_filter)).values('id')
            extra_filter = {f'{dimension}_id__in': subfilter}
        elif field and dimension.startswith('dim'):
            subfilter = DimensionText.objects.filter(
                self._text_to_filter(text_filter, text_fields=('text', 'text_local'))
            ).values('id')
            extra_filter = {f'{dimension}__in': subfilter}
        else:
            raise SlicerConfigError(
                'The requested dimension is not supported', SlicerConfigErrorCode.E107
            )
        return extra_annot, extra_filter

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

    def get_possible_dimension_values(
        self, dimension, max_values_count=100, ignore_self=False, text_filter=None, pks=None,
    ):
        """
        For a given dimension it returns which values are present in the filtered data and can thus
        be filtered/grouped on.
        If `ignore_self` is True, the dimensions themselves will not be used in the filter.
        """
        # we can ignore primary because it does not have any influence on the filtering
        self._replace_report_type_with_materialized(
            extra_dimensions_to_preserve={dimension}, ignore_primary=True
        )
        query = self.get_possible_dimension_values_queryset(dimension, ignore_self=ignore_self)
        # add text filter
        if text_filter:
            extra_annot, extra_filter = self.create_text_filter(dimension, text_filter)
            if extra_annot:
                query = query.annotate(**extra_annot)
            query = query.filter(**extra_filter)
        if pks:
            query = query.filter(**self.create_pk_filter(dimension, pks))
        # get count and decide if we need to sort
        count = query.count()
        cropped = False
        if max_values_count and count > max_values_count:
            cropped = True
            query = query.annotate(score=Coalesce(Sum('value'), 0)).order_by('-score')
            query = query[:max_values_count]
        return {'count': count, 'values': list(query), 'cropped': cropped}

    def get_possible_dimension_values_queryset(self, dimensions, ignore_self=False):
        if type(dimensions) not in (tuple, list, set):
            dimensions = [dimensions]
        ignore_dimensions = dimensions if ignore_self else None
        query = (
            self.accesslog_queryset(ignore_dimensions=ignore_dimensions)
            .values(*dimensions)
            .distinct()
        )
        return query

    def get_possible_groups_queryset(self):
        if self.group_by:
            return self.get_possible_dimension_values_queryset(self.group_by)
        return None

    def get_parts_queryset(self):
        if self.split_by:
            return self.get_possible_dimension_values_queryset(self.split_by)
        return None

    def get_data(self, lang='en', part: Optional[list] = None):
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
            if not dealt_with:
                obs.append(prefix + ob)
        qs = qs.order_by(*obs)
        return qs

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
                logger.info(
                    'Using materialized report: %s instead of %s', materialized_report, rt,
                )
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
    def filter_instance(cls, dimension, value):
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
        else:
            return filter_class(dimension, value)

    @classmethod
    def create_from_params(cls, params: dict) -> 'FlexibleDataSlicer':
        primary_dimension = params.get('primary_dimension')
        if not primary_dimension:
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
        order_by = params.get('order_by')
        if order_by:
            ob_field, _modifier = AccessLog.get_dimension_field(order_by)
            if isinstance(ob_field, ForeignKey):
                remote_cls = ob_field.remote_field.model
                try:
                    remote_cls._meta.get_field('name_en')
                except FieldDoesNotExist:
                    order_by = 'name'
                else:
                    order_by = 'name_en'
            desc = params.get('desc')
            if desc in (True, 'true', '1'):
                order_by = '-' + order_by
            slicer.order_by = [order_by]
        # extra stuff
        # the zero_rows value should be recoded to python bool, but we want to make sure
        slicer.include_all_zero_rows = params.get('zero_rows', '') in (True, 'true', '1', 1)
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
    """

    def __init__(self, message, code: SlicerConfigErrorCode, *args, details=None, **kwargs):
        self.message = message
        self.code = code.value
        self.details = details
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f'SlicerConfigError {self.code}: {self.message}'
