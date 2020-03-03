def extract_organization_id_from_request_query(request):
    return (request.query_params.get('organization') or
            request.query_params.get('organization_id'))


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
