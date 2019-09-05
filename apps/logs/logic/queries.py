"""
Functions that help in constructing django queries
"""
from typing import Iterable, Optional

from django.db import models
from django.db.models import Sum, Q
from django.shortcuts import get_object_or_404

from core.logic.dates import date_filter_from_params
from logs.logic.remap import remap_dicts
from logs.models import InterestGroup, AccessLog, ReportType, Dimension, DimensionText, \
    VirtualReportType


def interest_group_to_annot_name(ig: InterestGroup) -> str:
    return f'interest_{ig.pk}'


def interest_group_annotation_params(interest_groups: Iterable[InterestGroup],
                                     accesslog_filter: dict) -> dict:
    """
    :param interest_groups: list or queryset of interest groups
    :param accesslog_filter: filter to apply to all access logs in the summation
    :return:
    """
    interest_annot_params = {
        interest_group_to_annot_name(interest):
            Sum('accesslog__value',
                filter=Q(accesslog__metric__interest_group_id=interest.pk, **accesslog_filter))
        for interest in interest_groups
    }
    return interest_annot_params


def interest_value_to_annot_name(dt: DimensionText) -> str:
    return f'interest_{dt.pk}'


def interest_annotation_params(accesslog_filter: dict, interest_rt: ReportType) -> dict:
    """
    :param interest_rt: report type 'interest'
    :param accesslog_filter: filter to apply to all access logs in the summation
    :return:
    """
    interest_type_dim = interest_rt.dimensions_sorted[0]
    interest_annot_params = {
        interest_value_to_annot_name(interest_type):
            Sum('accesslog__value',
                filter=Q(accesslog__dim1=interest_type.pk,
                         accesslog__report_type=interest_rt,
                         **accesslog_filter))
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
    int_param_name_to_interest_type = {interest_value_to_annot_name(dt): dt
                                       for dt in interest_type_dim.dimensiontext_set.all()}
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
        params, dimensions=('date', 'platform', 'metric', 'organization', 'target')):
    query_params = {}
    for dim_name in dimensions:
        value = params.get(dim_name)
        if value:
            field = AccessLog._meta.get_field(dim_name)
            if isinstance(field, models.ForeignKey):
                if value not in (-1, '-1'):
                    query_params[dim_name] = get_object_or_404(field.related_model, pk=value)
                else:
                    # we ignore foreign keys with value -1
                    pass
            else:
                query_params[dim_name] = value
    return query_params


class StatsComputer(object):

    implicit_dims = ['date', 'platform', 'metric', 'organization', 'target', 'import_batch']
    input_dim_to_query_dim = {'interest': 'metric'}
    extra_query_params = {'interest': lambda rt: {'metric__reportinterestmetric__report_type': rt}}
    implicit_dim_to_text_fn = {'interest': lambda x: str(x)}

    def __init__(self):
        self.io_prim_dim_name = None  # name of dimension that was requested and will be outputed
        self.prim_dim_name = None
        self.prim_dim_obj = None
        self.io_sec_dim_name = None  # name of dimension that was requested and will be outputed
        self.sec_dim_name = None
        self.sec_dim_obj = None
        self.dim_raw_name_to_name = {}

    @classmethod
    def _translate_dimension_spec(cls, dim_name: str, report_type: ReportType) -> \
            (str, str, Optional[Dimension]):
        """
        Translate the value which is used to specify the dimension in request to the actual
        dimension for querying
        :param dim_name:
        :return: (output name of the dimension, name of dimension attr on AccessLog model,
                  Dimension instance if not implicit)
        """
        if dim_name is None:
            return None, None, None
        if dim_name in cls.input_dim_to_query_dim:
            return dim_name, cls.input_dim_to_query_dim[dim_name], None
        if dim_name in cls.implicit_dims:
            return dim_name, dim_name, None
        if isinstance(report_type, VirtualReportType):
            report_type = report_type.base_report_type
        dimensions = report_type.dimensions_sorted
        for dim_idx, dimension in enumerate(dimensions):
            if dimension.short_name == dim_name:
                break
        else:
            raise ValueError(f'Unknown dimension: {dim_name} for report type: {report_type}')
        return dimension.short_name, f'dim{dim_idx+1}', dimension

    def _extract_dimension_specs(self, report_type: ReportType, primary_dim: str,
                                 secondary_dim: Optional[str]):
        """
        Here we get the primary and secondary dimension name and corresponding objects from the
        request based on the report_type
        :param primary_dim: name of the dimension
        :param secondary_dim: name of the secondary dimension, may be None
        :param report_type: report type instance
        :return:
        """
        # decode the dimensions to find out what we need to have in the query
        self.io_prim_dim_name, self.prim_dim_name, self.prim_dim_obj = \
            self._translate_dimension_spec(primary_dim, report_type)
        self.io_sec_dim_name, self.sec_dim_name, self.sec_dim_obj = \
            self._translate_dimension_spec(secondary_dim, report_type)

    def get_data(self, report_type: ReportType, params: dict, user):
        """
        This method encapsulates most of the stuff that is done by this view.
        Based on report_type_id and the request object, it loads, post-processes, etc. the data
        and returns it
        :param report_type:
        :param params: dict with parameters, usually request.GET
        :user user: the user doing the querying
        :return:
        """
        secondary_dim = params.get('sec_dim')
        primary_dim = params.get('prim_dim', 'date')
        self._extract_dimension_specs(report_type, primary_dim, secondary_dim)
        # construct the query
        query, self.dim_raw_name_to_name = self.construct_query(report_type, params)
        # get the data - we need two separate queries for 1d and 2d cases
        if self.sec_dim_name:
            data = query \
                .values(self.prim_dim_name, self.sec_dim_name) \
                .annotate(count=Sum('value')) \
                .values(self.prim_dim_name, 'count', self.sec_dim_name) \
                .order_by(self.prim_dim_name, self.sec_dim_name)
        else:
            data = query.values(self.prim_dim_name) \
                .annotate(count=Sum('value')) \
                .values(self.prim_dim_name, 'count') \
                .order_by(self.prim_dim_name)
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
            if isinstance(report_type, ReportType):
                query_params = {'report_type': report_type, 'metric__active': True}
            else:
                query_params = {}
        else:
            query_params = {'metric__active': True}
        # go over implicit dimensions and add them to the query if GET params are given for this
        query_params.update(
            extract_accesslog_attr_query_params(params, dimensions=self.implicit_dims))
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
                            pass  # we leave the value as it is - it will probably lead to empty result
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
        # create the base query
        if report_type and isinstance(report_type, VirtualReportType):
            query = report_type.logdata_qs().filter(**query_params)
        else:
            query = AccessLog.objects.filter(**query_params)
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
            mapping = {obj.pk: obj for obj in field.related_model.objects.all()}
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
        for rec in data:
            if 'organization' in rec and rec['organization'] not in user_organizations:
                rec['organization'] = 'Anonym'
