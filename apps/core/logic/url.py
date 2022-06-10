import typing
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request


def extract_organization_id_from_request_query(request):
    return request.query_params.get('organization') or request.query_params.get('organization_id')


def extract_organization_id_from_request_data(request) -> (int, bool):
    """
    Returns the organization id from the request.data and a bool indicating if the key
    was present in the data (to distinguish between missing data and empty input value)
    :param request:
    :return:
    """
    for source in (request.data, request.GET):
        if 'organization' in source:
            return source.get('organization'), True
        if 'organization_id' in request.data:
            return source.get('organization_id'), True
    return None, False


def extract_field_from_request(request: Request, field_name: str) -> typing.Optional[int]:
    """
    Extracts attribte from request
    if attribute is present in data it has precedence over query parameters
    """

    try:
        # Try to get value from data
        value = request.data.get(field_name)
    except AttributeError:
        raise ValidationError('Malformed request')

    if not value:
        # Try to get value from query parameters
        value = request.query_params.get(field_name)

    if value:
        try:
            return int(value)
        except ValueError:
            raise ValidationError(f"Value of field '{field_name}' is not a valid integer ({value})")

    return None
