"""
Functions that help in constructing django queries
"""
from typing import Iterable

from django.db import models
from django.db.models import Sum, Q
from django.shortcuts import get_object_or_404

from logs.models import InterestGroup, AccessLog


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


def extract_interests_from_objects(interest_groups: Iterable[InterestGroup], objects: Iterable):
    """
    Goes over all objects in the list of objects and extracts all attributes that were created
    by first using the `interest_group_annotation_params` function to a separate attribute on
    the object called `interests`
    :param interest_groups: list or queryset of interest groups
    :param objects: objects of extraction
    :return:
    """
    ig_param_name_to_ig = {interest_group_to_annot_name(ig): ig for ig in interest_groups}
    for obj in objects:
        interests = {}
        for ig_param_name, ig in ig_param_name_to_ig.items():
            if hasattr(obj, ig_param_name):
                interests[ig.short_name] = {
                    'value': getattr(obj, ig_param_name),
                    'name': ig.name,
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
