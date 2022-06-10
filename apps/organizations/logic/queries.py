from django.http import Http404

from core.models import User


def organization_filter_from_org_id(
    org_id, user: User, prefix='', admin_required: bool = False, clickhouse=False
) -> dict:
    """
    Returns a filter parameters in form of a dictionary based on the org_id and the user
    If the org_id is -1 and the user has the proper role, all organizations should be allowed
    and thus the filter will be empty.
    :param prefix: prepended to the organization filter name if given, if set to None, the default
                   prefix 'organization' will be removed as well.
    :param org_id:
    :param admin_required: if True, admin access to the organization is required
    :param user:
    :return:
    """
    if org_id in ('-1', -1):
        if user.is_superuser or user.is_from_master_organization:
            return {}
        else:
            raise Http404()
    else:
        if type(org_id) is str and not org_id.isdigit():
            raise Http404()
        org_qs = user.admin_organizations() if admin_required else user.accessible_organizations()
        if (
            user.is_superuser
            or user.is_from_master_organization
            or org_qs.filter(pk=org_id).exists()
        ):
            # for django, we cannot use `organization_id` as it would not work for m2m links
            # in clickhouse we must use _id as __pk would not :)
            postfix = '_id' if clickhouse else '__pk'
            # if prefix is set to None, it signals direct filter on Organization and we do not
            # use the default 'organization' part of the attribute name
            attr_name = f'{prefix}organization{postfix}' if prefix is not None else 'pk'
            return {attr_name: org_id}
        raise Http404()


def extend_query_filter(filter_dict: dict, prefix: str) -> dict:
    return {prefix + key: value for key, value in filter_dict.items()}
