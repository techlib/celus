"""
Functions that help in constructing django queries
"""
import json
import logging
import operator
from base64 import b64decode
from collections import OrderedDict
from datetime import datetime, date
from functools import reduce
from typing import Iterable, Optional, Union, List, Type, Tuple, Callable

from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models import (
    Sum,
    Q,
    ForeignKey,
    FilteredRelation,
    DateField,
    IntegerField,
    Field,
    OuterRef,
    Subquery,
    Model,
    CharField,
    F,
)
from django.db.models.functions import Coalesce, Cast, Concat
from django.shortcuts import get_object_or_404

from charts.models import ReportDataView
from core.logic.dates import date_filter_from_params, date_range_from_params
from core.logic.serialization import parse_b64json
from core.logic.type_conversion import to_list
from logs.logic.csv_utils import MappingDictWriter
from logs.logic.remap import remap_dicts
from logs.models import AccessLog, ReportType, Dimension, DimensionText, Metric
from organizations.logic.queries import extend_query_filter
from organizations.models import Organization
from recache.util import recache_queryset

logger = logging.getLogger(__name__)


class TooMuchDataError(Exception):
    pass


class BadRequestError(Exception):
    pass


def interest_value_to_annot_name(dt: DimensionText) -> str:
    return f'interest_{dt.pk}'


def interest_annotation_params(
    accesslog_filter: dict, interest_rt: ReportType, prefix='accesslog__'
) -> dict:
    """
    :param interest_rt: report type 'interest'
    :param accesslog_filter: filter to apply to all access logs in the summation
    :return:
    """
    interest_type_dim = interest_rt.dimensions_sorted[0]
    interest_annot_params = {
        interest_value_to_annot_name(interest_type): Coalesce(
            Sum(
                prefix + 'value',
                filter=Q(**{prefix + 'dim1': interest_type.pk, prefix + 'report_type': interest_rt})
                & Q(**accesslog_filter),
            ),
            0,
        )
        for interest_type in interest_type_dim.dimensiontext_set.all()
    }
    return interest_annot_params


def extract_interests_from_objects(interest_rt: ReportType, objects: Iterable):
    """
    Goes over all objects in the list of objects and extracts all attributes that were created
    by first using the `interest_annotation_params` function to a separate attribute on
    the object called `interests`
    :param interest_rt: report type 'interest' instance
    :param objects: objects of extraction
    :return:
    """
    interest_type_dim = interest_rt.dimensions_sorted[0]
    int_param_name_to_interest_type = {
        interest_value_to_annot_name(dt): dt for dt in interest_type_dim.dimensiontext_set.all()
    }
    for obj in objects:
        interests = {}
        for int_param_name, dt in int_param_name_to_interest_type.items():
            if hasattr(obj, int_param_name):
                interests[dt.text] = {
                    'value': getattr(obj, int_param_name),
                    'name': dt.text_local,
                }
        obj.interests = interests


def extract_accesslog_attr_query_params(
    params,
    dimensions=('date', 'platform', 'metric', 'organization', 'target'),
    mdu_filter: bool = False,
    use_ids=False,
):
    """
    :param params: dict with the params
    :param dimensions:
    :param use_ids: when True, fk_id=Number will be used instead of fk=Instance
    :param mdu_filter: if True, a filter `mdu` will be extracted from the params - it is queried
                       differently than other dimensions, which is why it is treated separately
    :return:
    """
    query_params = {}
    for dim_name in dimensions:
        value = params.get(dim_name)
        if value:
            field = AccessLog._meta.get_field(dim_name)
            if isinstance(field, models.ForeignKey):
                if value not in (-1, '-1'):
                    if use_ids:
                        query_params[f'{dim_name}_id'] = value
                    else:
                        query_params[dim_name] = get_object_or_404(field.related_model, pk=value)
                else:
                    # we ignore foreign keys with value -1
                    pass
            else:
                query_params[dim_name] = value
    # MDUs are connected through import batches m2m, so we need to handle them differently
    if mdu_filter and (mdu_id := params.get('mdu')):
        query_params['import_batch__mdu__pk'] = mdu_id
    return query_params


def test_possible_materialized_report_use(
    query_params: {}, other_used_dimensions: Optional[Iterable] = None
) -> Optional[ReportType]:
    """
    Try to find a suitable materialized report for the one that is present in query params.
    It checks all the query params so that it does not
    select a report that would be missing some of the dimension needed for this query
    :param other_used_dimensions: list of other dimensions used by the query
    :param query_params: mapping of query attributes
    :return:
    """

    def normalize_param(param):
        if '__' in param:
            return normalize_param(param.split('__')[0])
        if param.endswith('_id'):
            return normalize_param(param[:-3])
        return param

    rt = query_params.get('report_type')
    if rt:
        normalized_query_params = {normalize_param(param) for param in query_params}
        if other_used_dimensions:
            normalized_query_params |= set(other_used_dimensions)
        return find_best_materialized_view(rt, normalized_query_params)


def replace_report_type_with_materialized(
    query_params: {}, other_used_dimensions: Optional[Iterable] = None
) -> bool:
    """
    Takes a list of parameters that would be passed as filter to Accesslog.objects.filter
    and tries to find a better suited report_type. If it finds one, it replaces it
    in the `query_params` dict (in place).
    :param other_used_dimensions: see `test_possible_materialized_report_use`
    :param query_params: see `test_possible_materialized_report_use`
    :return: did replacement take place
    """
    materialized_report = test_possible_materialized_report_use(
        query_params, other_used_dimensions=other_used_dimensions
    )
    if materialized_report:
        logger.info(
            'Using materialized report: %s instead of %s',
            materialized_report,
            query_params['report_type'],
        )
        query_params['report_type'] = materialized_report
        return True
    return False


def find_best_materialized_view(rt: ReportType, used_dimensions: [str]) -> Optional[ReportType]:
    """
    Takes a report_type and a list of dimensions that are to be present in the view and returns
    the best materialized view to use instead of the report type or None if none is available
    """
    # approx_record_count == 0 means that this is a new report type, not yet populated
    # and it would thus report back incorrect data
    candidates = ReportType.objects.filter(
        materialization_spec__base_report_type=rt, approx_record_count__gt=0
    )
    if candidates:
        used_dimensions = set(used_dimensions)
        final_candidates = []
        for candidate in candidates:
            kept, removed = candidate.materialization_spec.split_attributes()
            overlap = used_dimensions & set(removed)
            if overlap:
                # some of the params in used_dimensions are within removed, pity
                logger.debug('Removing candidate "%s" from list - it lacks %s', candidate, overlap)
            else:
                final_candidates.append(candidate)
                logger.debug('Candidate "%s" suitable when it comes to attrs', candidate)
        if final_candidates:
            if len(final_candidates) > 1:
                # we must decide upon the better one
                logger.debug('More than one candidate materialized report: %s', final_candidates)
                # we put the views with least number of dimensions first
                # (formerly we did query for accesslog count, but the extra queries were too costly
                #  and we need the solution fast rather then super optimal)
                to_sort = [
                    (
                        candidate.approx_record_count,
                        len(candidate.materialization_spec.kept_dimensions),
                        candidate,
                    )
                    for candidate in final_candidates
                ]
                to_sort.sort(key=lambda x: x[:2])
                logger.debug('Sorted candidates: %s, picking "%s"', to_sort, to_sort[0][2])
                return to_sort[0][2]
            else:
                return final_candidates[0]


class StatsComputer:

    implicit_dims = ['date', 'platform', 'metric', 'organization', 'target', 'import_batch']
    input_dim_to_query_dim = {'interest': 'metric'}
    extra_query_params = {'interest': lambda rt: {'metric__reportinterestmetric__report_type': rt}}
    implicit_dim_to_text_fn = {
        'interest': lambda x: str(x),
        'metric': lambda x: x.name or x.short_name,
    }
    hard_result_count_limit = 20_000

    def __init__(self):
        self.io_prim_dim_name = None  # name of dimension that was requested and will be outputted
        self.prim_dim_name = None
        self.prim_dim_obj = None
        self.io_sec_dim_name = None  # name of dimension that was requested and will be outputted
        self.sec_dim_name = None
        self.sec_dim_obj = None
        self.dim_raw_name_to_name = {}
        self.reported_metrics = {}
        # the following represents the report type that was actually used to make the db query
        # if a materialized report is used later on, the following value will be changed
        # to the new report type in order to signal the change to the outside
        self.used_report_type = None

    def _translate_dimension_spec(self, dim_name: str) -> (str, str, Optional[Dimension]):
        """
        Translate the value which is used to specify the dimension in request to the actual
        dimension for querying
        :param dim_name:
        :return: (output name of the dimension, name of dimension attr on AccessLog model,
                  Dimension instance if not implicit)
        """
        # we support Django style __ for date parts and related fields references
        # here we split the name before processing if __ is present
        rest = ''
        if dim_name and '__' in dim_name:
            dim_name, rest = dim_name.split('__', 1)

        if dim_name is None:
            return None, None, None
        if dim_name in self.input_dim_to_query_dim:
            return dim_name, self.input_dim_to_query_dim[dim_name], None
        if dim_name in self.implicit_dims:
            # this is the only place where we use the split version of dim_name (for now)
            if rest:
                return dim_name, f'{dim_name}__{rest}', None
            else:
                return dim_name, dim_name, None
        dimensions = self.used_report_type.dimensions_sorted
        for dim_idx, dimension in enumerate(dimensions):
            if dimension.short_name == dim_name:
                break
        else:
            raise BadRequestError(
                f'Unknown dimension: "{dim_name}" for report type: "{self.used_report_type}"'
            )
        return dimension.short_name, f'dim{dim_idx+1}', dimension

    def _extract_dimension_specs(self, primary_dim: str, secondary_dim: Optional[str]):
        """
        Here we get the primary and secondary dimension name and corresponding objects from the
        request based on the report_type
        :param primary_dim: name of the dimension
        :param secondary_dim: name of the secondary dimension, may be None
        :return:
        """
        # decode the dimensions to find out what we need to have in the query
        (
            self.io_prim_dim_name,
            self.prim_dim_name,
            self.prim_dim_obj,
        ) = self._translate_dimension_spec(primary_dim)
        self.io_sec_dim_name, self.sec_dim_name, self.sec_dim_obj = self._translate_dimension_spec(
            secondary_dim
        )

    def get_data(
        self, report_type: Union[ReportType, ReportDataView], params: dict, user, recache=False
    ):
        """
        This method encapsulates most of the stuff that is done by this view.
        Based on report_type_id and the request object, it loads, post-processes, etc. the data
        and returns it
        :param report_type:
        :param params: dict with parameters, usually request.GET
        :param user: the user doing the querying
        :param recache: should recache be used to cache the database query?
        :return:
        """
        secondary_dim = params.get('sec_dim')
        primary_dim = params.get('prim_dim', 'date')
        self.used_report_type = (
            report_type.base_report_type if isinstance(report_type, ReportDataView) else report_type
        )
        self._extract_dimension_specs(primary_dim, secondary_dim)
        # construct the query
        query, self.dim_raw_name_to_name = self.construct_query(report_type, params)
        # get the data - we need two separate queries for 1d and 2d cases
        if self.sec_dim_name:
            data = (
                query.values(self.prim_dim_name, self.sec_dim_name)
                .annotate(count=Sum('value'))
                .values(self.prim_dim_name, 'count', self.sec_dim_name)
                .order_by(self.prim_dim_name, self.sec_dim_name)
            )
        else:
            data = (
                query.values(self.prim_dim_name)
                .annotate(count=Sum('value'))
                .values(self.prim_dim_name, 'count')
                .order_by(self.prim_dim_name)
            )
        if recache:
            data = recache_queryset(data, origin='chart-data')
        if len(data) > self.hard_result_count_limit:
            logger.warning(
                'Result size of %d exceeded the limit of %d records',
                len(data),
                self.hard_result_count_limit,
            )
            raise TooMuchDataError()
        self.post_process_data(data, user)
        return data

    def post_process_data(self, data, user):
        # clean names of organizations
        self.clean_organization_names(user, data)
        # remap the values if text dimensions are involved
        # primary dimension
        if self.prim_dim_obj and self.prim_dim_obj.type == Dimension.TYPE_TEXT:
            remap_dicts(self.prim_dim_obj, data, self.prim_dim_name)
        elif self.prim_dim_name in self.implicit_dims:
            # we remap the implicit dims if they are foreign key based
            to_text_fn = self.implicit_dim_to_text_fn.get(self.io_prim_dim_name, str)
            self.remap_implicit_dim(data, self.prim_dim_name, to_text_fn=to_text_fn)
        # secondary dimension
        if self.sec_dim_obj and self.sec_dim_obj.type == Dimension.TYPE_TEXT:
            remap_dicts(self.sec_dim_obj, data, self.sec_dim_name)
        elif self.sec_dim_name in self.implicit_dims:
            # we remap the implicit dims if they are foreign key based
            to_text_fn = self.implicit_dim_to_text_fn.get(self.io_sec_dim_name, str)
            self.remap_implicit_dim(data, self.sec_dim_name, to_text_fn=to_text_fn)
        # remap dimension names
        if self.prim_dim_name in self.dim_raw_name_to_name:
            new_prim_dim_name = self.dim_raw_name_to_name[self.prim_dim_name]
            for rec in data:
                rec[new_prim_dim_name] = rec[self.prim_dim_name]
                del rec[self.prim_dim_name]
        if self.sec_dim_name in self.dim_raw_name_to_name:
            new_sec_dim_name = self.dim_raw_name_to_name[self.sec_dim_name]
            for rec in data:
                rec[new_sec_dim_name] = rec[self.sec_dim_name]
                del rec[self.sec_dim_name]

    def construct_query(self, report_type, params):
        if report_type:
            query_params = {'report_type': self.used_report_type, 'metric__active': True}
        else:
            query_params = {'metric__active': True}
        # go over implicit dimensions and add them to the query if GET params are given for this
        query_params.update(
            extract_accesslog_attr_query_params(
                params, dimensions=self.implicit_dims, mdu_filter=True
            )
        )
        # now go over the extra dimensions and add them to filter if requested
        dim_raw_name_to_name = {}
        if report_type:
            for i, dim in enumerate(report_type.dimensions_sorted):
                dim_raw_name = 'dim{}'.format(i + 1)
                dim_name = dim.short_name
                dim_raw_name_to_name[dim_raw_name] = dim_name
                value = params.get(dim_name)
                if value:
                    if dim.type == dim.TYPE_TEXT:
                        try:
                            value = DimensionText.objects.get(dimension=dim, text=value).pk
                        except DimensionText.DoesNotExist:
                            # we leave the value as it is - it will probably lead to empty result
                            pass
                    query_params[dim_raw_name] = value
        # remap dimension names if the query dim name is different from the i/o one
        if self.prim_dim_name != self.io_prim_dim_name:
            dim_raw_name_to_name[self.prim_dim_name] = self.io_prim_dim_name
        if self.sec_dim_name != self.io_sec_dim_name:
            dim_raw_name_to_name[self.sec_dim_name] = self.io_sec_dim_name
        # add extra filters if requested
        prim_extra = self.extra_query_params.get(self.io_prim_dim_name)
        if prim_extra:
            query_params.update(prim_extra(report_type))
        sec_extra = self.extra_query_params.get(self.io_sec_dim_name)
        if sec_extra:
            query_params.update(sec_extra(report_type))
        # add filter for dates
        query_params.update(date_filter_from_params(params))

        # maybe use materialized report if available
        extra_dims = {self.prim_dim_name}
        if self.sec_dim_name:
            extra_dims.add(self.sec_dim_name)
        rt_change = replace_report_type_with_materialized(
            query_params, other_used_dimensions=extra_dims
        )
        # we preserve the original value of used_report_type for use in later code
        original_used_report_type = self.used_report_type
        if rt_change:
            self.used_report_type = query_params.get('report_type')

        # construct the query
        query = AccessLog.objects.filter(**query_params)
        if report_type and isinstance(report_type, ReportDataView):
            query = query.filter(**report_type.accesslog_filters)

        # filter to only interest metrics if metric neither primary nor secondary dim
        if report_type and self.prim_dim_name != 'metric' and self.sec_dim_name != 'metric':
            # Rationale: summing up different metrics together does not make much sense
            # for example Total_Item_Requests and Unique_Item_Requests are dependent on each
            # other and in fact the latter is a subset of the former. Thus we only use the
            # metrics that define interest for computation if metric itself is not the primary
            # or secondary dimension
            # Technical note: putting the filter into the query leads to a very slow response
            # (2500 ms instead of 60 ms in a test case) - this is why we get the pks of the metrics
            # first and then use the "in" filter.
            self.reported_metrics = {
                im.pk: im for im in original_used_report_type.interest_metrics.order_by()
            }
            if self.reported_metrics:
                query = query.filter(metric_id__in=self.reported_metrics.keys())
            else:
                # if there are no interest metrics associated with the report_type
                # we need to tell the user that all possible metrics were used
                used_metric_ids = {rec['metric_id'] for rec in query.values('metric_id').distinct()}
                self.reported_metrics = {
                    im.pk: im for im in Metric.objects.filter(pk__in=used_metric_ids)
                }
        return query, dim_raw_name_to_name

    @classmethod
    def remap_implicit_dim(cls, data, dim_name, to_text_fn=str):
        """
        Remaps foreign keys to the corresponding values
        :param to_text_fn: function applied to the resolved object to extract text from it
        :param data: values
        :param dim_name: name of the AccessLog attribute of this dimension
        :return:
        """
        field = AccessLog._meta.get_field(dim_name)
        if isinstance(field, models.ForeignKey):
            unique_values = {rec[dim_name] for rec in data if type(rec[dim_name]) is int}
            mapping = {
                obj.pk: obj for obj in field.related_model.objects.filter(pk__in=unique_values)
            }
            for rec in data:
                if rec[dim_name] in mapping:
                    rec[dim_name] = to_text_fn(mapping[rec[dim_name]]).replace('_', ' ')

    @classmethod
    def clean_organization_names(cls, user, data):
        """
        If organization is present in the data, we need to anonymize the data for those
        organizations that the user does not have access to.
        :param user: instance of the current user
        :param data: records to be cleaned - organizations should be passed as their primary key
        :return:
        """
        user_organizations = {org.pk for org in user.accessible_organizations()}
        org_nums = []
        for rec in data:
            if 'organization' in rec and rec['organization'] not in user_organizations:
                org = rec['organization']
                try:
                    num = org_nums.index(org) + 1
                except ValueError:
                    org_nums.append(org)
                    num = len(org_nums)
                rec['organization'] = 'Anonym-{:03d}'.format(num)


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
    """

    def __init__(self, message, code, *args, details=None, **kwargs):
        self.message = message
        self.code = code
        self.details = details
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f'SlicerConfigError {self.code}: {self.message}'


class DimensionFilter:
    def __init__(self, dimension):
        self.dimension = dimension

    def query_params(self, primary_filter=False) -> dict:
        """
        When `primary_filter` is False, the filter params should be returned for the AccessLog model
        if `primary_filter` is True, it should be for the dimension model itself
        :param primary_filter:
        :return:
        """
        raise NotImplementedError()

    def config(self):
        raise NotImplementedError()


class DateDimensionFilter(DimensionFilter):
    def __init__(self, dimension, start, end):
        super().__init__(dimension)
        self.start = start
        self.end = end

    def query_params(self, primary_filter=False) -> dict:
        ret = {}
        if self.start:
            ret[f'{self.dimension}__gte'] = self.start
        if self.end:
            ret[f'{self.dimension}__lte'] = self.end
        return ret

    def config(self):
        return {
            'dimension': self.dimension,
            'start': self.serialize_date(self.start),
            'end': self.serialize_date(self.end),
        }

    @classmethod
    def serialize_date(cls, value):
        if isinstance(value, datetime):
            return value.date().isoformat()
        elif isinstance(value, date):
            return value.isoformat()
        return value


class ForeignKeyDimensionFilter(DimensionFilter):
    def __init__(self, dimension, values):
        super().__init__(dimension)
        values = to_list(values)
        # convert model instances to their primary keys
        values = [val.pk if isinstance(val, models.Model) else val for val in values]
        self.values = values

    def query_params(self, primary_filter=False) -> dict:
        if primary_filter:
            return {'pk__in': self.values}
        return {f'{self.dimension}_id__in': self.values}

    def config(self):
        return {
            'dimension': self.dimension,
            'values': self.values,
        }


class ExplicitDimensionFilter(DimensionFilter):
    def __init__(self, dimension, values):
        super().__init__(dimension)
        self.values = to_list(values)

    def query_params(self, primary_filter=False) -> dict:
        return {f'{self.dimension}__in': self.values}

    def config(self):
        return {
            'dimension': self.dimension,
            'values': self.values,
        }


class FlexibleDataSlicer:
    implicit_dims = ['date', 'platform', 'metric', 'organization', 'target', 'report_type']

    def __init__(self, primary_dimension):
        self.primary_dimension = primary_dimension
        self.dimension_filters: List[DimensionFilter] = []
        self.group_by = []
        self.order_by = []
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
                'E100',
            )

    def check_params_for_data_query(self):
        """
        Extra checks to be performed before data query is run. These do not apply to other functions,
        such as getting possible dimension values.
        """
        if not self.group_by:
            raise SlicerConfigError(
                'At least one "group" dimension must be given to define the output columns', 'E106'
            )

    def accesslog_queryset(self, ignore_dimensions=None):
        self.check_params()
        query_params = self.create_filters(ignore_dimensions=ignore_dimensions)
        return AccessLog.objects.filter(**query_params)

    def get_queryset(self):
        self.check_params()
        self.check_params_for_data_query()
        field, modifier = self.get_dimension_field(self.primary_dimension)
        if isinstance(field, ForeignKey):
            primary_cls = field.remote_field.model
            qs = primary_cls.objects.all()
            if primary_cls is Organization and self.organization_filter is not None:
                qs = qs.filter(pk__in=self.organization_filter)
            qs = (
                qs.filter(**self._primary_dimension_filter())
                .annotate(
                    relevant_accesslogs=FilteredRelation(
                        'accesslog', condition=Q(**extend_query_filter(self.filters, 'accesslog__'))
                    )
                )
                .values('pk')
                .annotate(**self._prepare_annotations())
            )
        elif field and self.primary_dimension.startswith('dim'):
            qs = (
                AccessLog.objects.filter(**self.filters)
                .values(self.primary_dimension)
                .distinct()
                .annotate(**self._prepare_annotations(accesslog_prefix=''))
            )
        elif field and isinstance(field, DateField):
            if modifier and modifier != 'year':
                raise ValueError('The only modifier allowed for date is "year", i.e. date__year')
            qs = (
                AccessLog.objects.filter(**self.filters)
                .values(self.primary_dimension)
                .distinct()
                .annotate(**self._prepare_annotations(accesslog_prefix=''))
            )
        elif field:
            raise SlicerConfigError(
                f'Primary dimension {self.primary_dimension} is not supported',
                'E102',
                details={'dimension': self.primary_dimension},
            )
        else:
            raise SlicerConfigError(
                f'Primary dimension {self.primary_dimension} is not valid',
                'E103',
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
                'E101',
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

    @classmethod
    def get_dimension_field(cls, dimension) -> Tuple[Optional[Field], Optional[str]]:
        modifier = ''
        if '__' in dimension:
            dimension, modifier = dimension.split('__', 1)
        try:
            return AccessLog._meta.get_field(dimension), modifier
        except FieldDoesNotExist:
            return None, None

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
        field, modifier = self.get_dimension_field(dimension)
        extra_filter = {}
        extra_annot = {}
        if isinstance(field, ForeignKey):
            primary_cls = field.remote_field.model
            subfilter = primary_cls.objects.filter(self._text_to_filter(text_filter)).values('id')
            extra_filter = {f'{dimension}_id__in': subfilter}
        elif field and dimension.startswith('dim'):
            dim = self.resolve_explicit_dimension(dimension)
            if dim.type == Dimension.TYPE_TEXT:
                subfilter = DimensionText.objects.filter(
                    self._text_to_filter(text_filter, text_fields=('text', 'text_local'))
                ).values('id')
                extra_filter = {f'{dimension}__in': subfilter}
            else:
                extra_annot = {f'{dimension}_str': Cast(dimension, CharField())}
                extra_filter = {f'{dimension}_str__contains': text_filter}
        else:
            raise SlicerConfigError('The requested dimension is not supported', 'E107')
        return extra_annot, extra_filter

    @classmethod
    def create_pk_filter(cls, dimension, pks: list) -> dict:
        """
        Creates a dict that can be used in queryset filter to filter only those instances of
        `dimension` which have their pk in the list of `pks`.
        """
        field, modifier = cls.get_dimension_field(dimension)
        if isinstance(field, ForeignKey):
            extra_filter = {f'{dimension}_id__in': pks}
        elif field and dimension.startswith('dim'):
            extra_filter = {f'{dimension}__in': pks}
        else:
            raise SlicerConfigError('The requested dimension is not supported', 'E107')
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

    def get_data(self, lang='en'):
        # we do the following just before getting data in order to ensure the slicer is finalized
        # TODO: we could lock the slicer for further changes after that
        self._replace_report_type_with_materialized()
        qs = self.get_queryset()
        obs = []
        for ob in self.order_by:
            prefix = '-' if ob.startswith('-') else ''
            ob = ob.lstrip('-')
            dealt_with = False
            if ob.startswith('dim'):
                # when sorting by dimX we need to map the IDs to the corresponding texts
                # because the mapping does not use a Foreign key relationship, we use a subquery
                # but the dimension might be of type 'integer' and in such case we do not want to
                # remap anything...
                dim = self.resolve_explicit_dimension(ob)
                if dim.type == Dimension.TYPE_TEXT:
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
        field, _modifier = cls.get_dimension_field(dimension)
        if isinstance(field, ForeignKey):
            return ForeignKeyDimensionFilter
        elif isinstance(field, DateField):
            return DateDimensionFilter
        elif isinstance(field, IntegerField):
            return ExplicitDimensionFilter
        else:
            raise ValueError(f'not supported yet ({dimension}, {field}, {_modifier})')

    @classmethod
    def create_from_params(cls, params: dict) -> 'FlexibleDataSlicer':
        primary_dimension = params.get('primary_dimension')
        if not primary_dimension:
            raise SlicerConfigError('"primary_dimension" key must be present', 'E104')
        slicer = cls(primary_dimension)
        # filters
        filters = params.get('filters')
        filters = parse_b64json(filters) if filters else {}
        for key, value in filters.items():
            filter_class = cls.filter_class(key)
            if filter_class is DateDimensionFilter:
                dim_filter = filter_class(key, *date_range_from_params(value))
            else:
                dim_filter = filter_class(key, value)
            slicer.add_filter(dim_filter)
        # groups
        groups = params.get('groups')
        groups = parse_b64json(groups) if groups else []
        for group in groups:
            slicer.add_group_by(group)
        # ordering
        order_by = params.get('order_by')
        if order_by:
            ob_field, _modifier = cls.get_dimension_field(order_by)
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
            raise SlicerConfigError('"primary_dimension" key must be present', 'E104')
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
        # ordering
        slicer.order_by = params.get('order_by', [])
        # extra stuff
        slicer.include_all_zero_rows = params.get('zero_rows', False)
        return slicer


class FlexibleDataExporter:

    object_remapped_dims = {'target': {'columns': ['name', 'issn', 'eissn', 'isbn']}}

    def __init__(self, slicer: FlexibleDataSlicer, column_parts_separator: str = ' / '):
        self.slicer = slicer
        self.involved_report_types = self.slicer.involved_report_types()
        self.column_parts_separator = column_parts_separator
        self.explicit_prim_dim, self.remapped_prim_dim, prim_dim = self.resolve_dimension(
            self.slicer.primary_dimension
        )
        # how the primary dimension is called in the query output
        self.prim_dim_key = self.slicer.primary_dimension
        if self.remapped_prim_dim:
            if self.explicit_prim_dim:
                self.prim_dim_remap = {
                    obj['pk']: obj['text']
                    for obj in DimensionText.objects.filter(dimension=prim_dim).values('pk', 'text')
                }
            else:
                self.prim_dim_remap = {
                    obj['pk']: obj
                    for obj in prim_dim.objects.all().values('pk', *self.remapped_keys())
                }
                self.prim_dim_key = 'pk'
        else:
            self.prim_dim_remap = {}

    def remapped_keys(self):
        return self.object_remapped_dims.get(self.slicer.primary_dimension, {}).get(
            'columns', ['name']
        )

    def stream_data_to_sink(
        self, sink, progress_monitor: Optional[Callable[[int, int], None]] = None
    ) -> int:
        """
        If progress monitor is given, it will be called with a tuple (current_count, total_count)
        for each bunch of exported rows. It will also be called at the end of export.

        Please note that in order to calculate the total the query has to be run twice
        which might incur some time penalty.

        Returns the number of written rows
        """
        qs = self.slicer.get_data()
        total = 0
        if progress_monitor:
            # we put out the total as soon as possible
            total = qs.count()
            progress_monitor(0, total)
        data = qs.iterator()
        try:
            row = next(data)
        except StopIteration:
            return 0
        fields = [(self.prim_dim_key, self.slicer.primary_dimension)]
        # possible other remapped attrs of primary object
        remap_keys = self.remapped_keys()
        for key in remap_keys[1:]:
            fields.append((key, key.upper()))
        # fields from groups
        other_fields = []
        for key in row:
            if key.startswith('grp-'):
                other_fields.append((key, self.remap_column_name(key)))
        # sort columns by their remapped name
        other_fields.sort(key=lambda x: (x[1], x[0]))
        fields += other_fields
        writer = MappingDictWriter(sink, fields=fields)
        self.writerow(writer, row)
        count = 1
        for i, row in enumerate(data):
            self.writerow(writer, row)
            count += 1
            if progress_monitor and count % 100 == 0:
                progress_monitor(count, total)
        if progress_monitor:
            progress_monitor(total, total)
        return count

    def writerow(self, writer, row):
        if self.remapped_prim_dim:
            if self.explicit_prim_dim:
                # remap to text using the DimensionText mapping - mapper converts directly to text
                row[self.prim_dim_key] = self.prim_dim_remap.get(
                    row[self.prim_dim_key], row[self.prim_dim_key]
                )
            else:
                # mapper converts to dict
                remap_data = self.prim_dim_remap.get(row[self.prim_dim_key], {})
                # remap the first column
                remap_keys = self.remapped_keys()
                row[self.prim_dim_key] = remap_data.get(remap_keys[0], row[self.prim_dim_key])
                for key in remap_keys[1:]:
                    # remap all other keys
                    row[key] = remap_data.get(key, '')
        writer.writerow(row)

    def remap_column_name(self, column):
        parts = self.slicer.decode_key(column)
        name_parts = []
        for key, value in parts.items():
            name_parts.append(self.dimension_remap(key, value))
        return self.column_parts_separator.join(name_parts)

    def dimension_remap(self, dimension, value):
        if value is None:
            return '-'
        explicit, remapped, dim_model = self.resolve_dimension(dimension)
        if remapped:
            if explicit:
                obj = DimensionText.objects.get(pk=value)
                return obj.text_local or obj.text
            else:
                obj = dim_model.objects.get(pk=value)
                return obj.name or obj.short_name
        else:
            return str(value)

    def resolve_dimension(self, ref) -> Tuple[bool, bool, Optional[Model]]:
        """
        :param ref: attribute name referencing this dimension in AccessLog
        :return: (explicit, remapped, Dimension instance or references model)
        """
        field, modifier = self.slicer.get_dimension_field(ref)
        if isinstance(field, ForeignKey):
            return False, True, field.remote_field.model
        elif ref.startswith('dim'):
            # we need the report types to deal with this
            if len(self.involved_report_types) != 1:
                raise ValueError(
                    'Exactly one report type should be active when resolving explicit dimensions'
                )
            rt: ReportType = self.involved_report_types[0]
            dim = rt.dimension_by_attr_name(ref)
            return True, dim.type == dim.TYPE_TEXT, dim
        else:
            return False, False, None
