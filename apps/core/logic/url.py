def extract_organization_id_from_request_query(request):
    return (request.query_params.get('organization') or
            request.query_params.get('organization_id'))


def extract_organization_id_from_request_data(request):
    return (request.data.get('organization') or
            request.data.get('organization_id'))
