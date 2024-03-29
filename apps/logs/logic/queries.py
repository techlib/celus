"""
Functions that help in constructing django queries
"""
import logging
from typing import Iterable, Optional, Union

from charts.models import ReportDataView
from core.logic.dates import date_filter_from_params
from django.db import models
from django.db.models import Exists, OuterRef, Q, QuerySet, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from logs.logic.remap import remap_dicts
from logs.models import (
    AccessLog,
    Dimension,
    DimensionText,
    ManualDataUpload,
    Metric,
    ReportInterestMetric,
    ReportType,
)
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
                interests[dt.text] = {'value': getattr(obj, int_param_name), 'name': dt.text_local}
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
        # Postgres sometimes has trouble efficiently planning the query when the mdu filter is
        # applied, and it takes a long time to execute. Maybe it has to do with the extra
        # partitioning on K1, I am not sure.
        # We help it by providing extra context derived from the MDU (I got something like 80x
        # speed-up in one case on K1)
        try:
            mdu = ManualDataUpload.objects.get(pk=mdu_id)
        except ManualDataUpload.DoesNotExist:
            pass
        else:
            if mdu.organization:
                query_params['organization'] = mdu.organization
            query_params['platform_id'] = mdu.platform_id
            query_params['report_type_id'] = mdu.report_type_id
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

    def __init__(self, report_type: Union[ReportType, ReportDataView], params: dict):
        # basic setup
        self.io_prim_dim_name = None  # name of dimension that was requested and will be outputted
        self.prim_dim_name = None
        self.prim_dim_obj = None
        self.io_sec_dim_name = None  # name of dimension that was requested and will be outputted
        self.sec_dim_name = None
        self.sec_dim_obj = None
        self.dim_raw_name_to_name = {}
        self.reported_metrics = {}
        self.dim_raw_name_to_name = {}  # gets filled in during query preparation
        self.query: Optional[QuerySet] = None

        # storage and pre-processing of params
        self.report_type = report_type
        self.params = params
        # the following represents the report type that was actually used to make the db query
        # if a materialized report is used later on, the following value will be changed
        # to the new report type in order to signal the change to the outside
        self.used_report_type = (
            self.report_type.base_report_type
            if isinstance(self.report_type, ReportDataView)
            else self.report_type
        )
        # `used_report_type` may be replaced by a materialized report later on
        # here we present the original report type
        self.original_used_report_type = self.used_report_type
        # decode the dimensions to find out what we need to have in the query
        (
            self.io_prim_dim_name,
            self.prim_dim_name,
            self.prim_dim_obj,
        ) = self._translate_dimension_spec(params.get('prim_dim', 'date'))
        self.io_sec_dim_name, self.sec_dim_name, self.sec_dim_obj = self._translate_dimension_spec(
            params.get('sec_dim')
        )
        # construct the accesslog query
        self.query = self.construct_accesslog_query()

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

    def get_data(self, user, recache=False):
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
        # we use the prepared self.query where accesslogs are filtered
        # we just need to enforce one-metric rule if metric is not specified in the request
        self.enforce_metric_filter()
        # get the data - we need two separate queries for 1d and 2d cases
        if self.sec_dim_name:
            data = (
                self.query.values(self.prim_dim_name, self.sec_dim_name)
                .annotate(count=Sum('value'))
                .values(self.prim_dim_name, 'count', self.sec_dim_name)
                .order_by(self.prim_dim_name, self.sec_dim_name)
            )
        else:
            data = (
                self.query.values(self.prim_dim_name)
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
        if self.prim_dim_obj:
            remap_dicts(self.prim_dim_obj, data, self.prim_dim_name)
        elif self.prim_dim_name in self.implicit_dims:
            # we remap the implicit dims if they are foreign key based
            to_text_fn = self.implicit_dim_to_text_fn.get(self.io_prim_dim_name, str)
            self.remap_implicit_dim(data, self.prim_dim_name, to_text_fn=to_text_fn)
        # secondary dimension
        if self.sec_dim_obj:
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

    def construct_accesslog_query(self) -> QuerySet[AccessLog]:
        if self.report_type:
            query_params = {'report_type': self.used_report_type, 'metric__active': True}
        else:
            query_params = {'metric__active': True}
        # go over implicit dimensions and add them to the query if GET params are given for this
        query_params.update(
            extract_accesslog_attr_query_params(
                self.params, dimensions=self.implicit_dims, mdu_filter=True
            )
        )
        # now go over the extra dimensions and add them to filter if requested
        self.dim_raw_name_to_name = {}
        if self.report_type:
            for i, dim in enumerate(self.report_type.dimensions_sorted):
                dim_raw_name = 'dim{}'.format(i + 1)
                dim_name = dim.short_name
                self.dim_raw_name_to_name[dim_raw_name] = dim_name
                value = self.params.get(dim_name)
                if value:
                    try:
                        value = DimensionText.objects.get(dimension=dim, text=value).pk
                    except DimensionText.DoesNotExist:
                        # we leave the value as it is - it will probably lead to empty result
                        pass
                    query_params[dim_raw_name] = value
        # remap dimension names if the query dim name is different from the i/o one
        if self.prim_dim_name != self.io_prim_dim_name:
            self.dim_raw_name_to_name[self.prim_dim_name] = self.io_prim_dim_name
        if self.sec_dim_name != self.io_sec_dim_name:
            self.dim_raw_name_to_name[self.sec_dim_name] = self.io_sec_dim_name
        # add extra filters if requested
        prim_extra = self.extra_query_params.get(self.io_prim_dim_name)
        if prim_extra:
            query_params.update(prim_extra(self.report_type))
        sec_extra = self.extra_query_params.get(self.io_sec_dim_name)
        if sec_extra:
            query_params.update(sec_extra(self.report_type))
        # add filter for dates
        query_params.update(date_filter_from_params(self.params))

        # maybe use materialized report if available
        extra_dims = {self.prim_dim_name}
        if self.sec_dim_name:
            extra_dims.add(self.sec_dim_name)
        rt_change = replace_report_type_with_materialized(
            query_params, other_used_dimensions=extra_dims
        )
        if rt_change:
            # the original value is still preserved in self.original_used_report_type
            self.used_report_type = query_params.get('report_type')

        # construct the query
        query = AccessLog.objects.filter(**query_params)
        if self.report_type and isinstance(self.report_type, ReportDataView):
            query = query.filter(**self.report_type.accesslog_filters)
        return query

    def get_available_metrics(self) -> QuerySet[Metric]:
        used_metric_ids = set(self.query.values_list('metric_id', flat=True).distinct())
        return Metric.objects.filter(pk__in=used_metric_ids).annotate(
            is_interest_metric=Exists(
                ReportInterestMetric.objects.filter(
                    metric_id=OuterRef('pk'), report_type_id=self.original_used_report_type.pk
                )
            )
        )

    def enforce_metric_filter(self) -> None:
        """
        If metric is neither the primary nor the secondary dimension, we need to filter the
        results to contain only metrics that can be summed up.

        Rationale: summing up different metrics together does not make much sense
        for example Total_Item_Requests and Unique_Item_Requests are dependent on each
        other and in fact the latter is a subset of the former. Thus we only use the
        metrics that define interest for computation if metric itself is not the primary
        or secondary dimension
        """
        # filter to only interest metrics if metric neither primary nor secondary dim
        if (
            self.report_type
            and self.prim_dim_name != 'metric'
            and self.sec_dim_name != 'metric'
            and 'metric' not in self.params
        ):
            interest_metrics = set(
                self.original_used_report_type.interest_metrics.order_by().values_list(
                    'pk', flat=True
                )
            )
            if interest_metrics:
                self.query = self.query.filter(metric_id__in=interest_metrics)

            # we want to list only the metrics which are actually used - regardless of
            # interest_metrics
            used_metric_ids = set(self.query.values_list('metric_id', flat=True).distinct())
            self.reported_metrics = {
                im.pk: im for im in Metric.objects.filter(pk__in=used_metric_ids)
            }

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
