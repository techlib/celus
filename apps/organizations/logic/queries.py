from django.http import Http404

from core.models import User


def organization_filter_from_org_id(org_id, user: User, prefix='') -> dict:
    """
    Returns a filter parameters in form of a dictionary based on the org_id and the user
    If the org_id is -1 and the user has the proper role, all organizations should be allowed
    and thus the filter will be empty.
    :param prefix: prepended to the organization filter name if given
    :param org_id:
    :param user:
    :return:
    """
    if org_id in ('-1', -1):
        if user.is_from_master_organization:
            return {}
        else:
            raise Http404()
    else:
        if not (user.organizations.filter(pk=org_id).exists() or user.is_from_master_organization):
            raise Http404()
        return {f'{prefix}organization__pk': org_id}


def extend_query_filter(filter_dict: dict, prefix: str) -> dict:
    return {prefix + key: value for key, value in filter_dict.items()}
