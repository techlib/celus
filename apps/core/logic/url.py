def extract_organization_id_from_request(request):
    return (request.query_params.get('organization') or
            request.query_params.get('organization_id') or
            request.data.get('organization') or
            request.data.get('organization_id'))
