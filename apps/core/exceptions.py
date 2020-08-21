from rest_framework.exceptions import APIException


class BadRequestException(APIException):

    """
    Exception to be used when we need to trigger 400 error response from a view.
    """

    status_code = 400
    default_code = 'bad request'
    default_detail = 'Incorrect input data for the request'
