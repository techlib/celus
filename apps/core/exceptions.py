from rest_framework.exceptions import APIException


class BadRequestException(APIException):

    """
    Exception to be used when we need to trigger 400 error response from a view.
    """

    status_code = 400
    default_code = 'bad request'
    default_detail = 'Incorrect input data for the request'


class ModelUsageError(Exception):
    """
    Used when a model is used in a way that is not allowed or supported.
    """


class FileConsistencyError(Exception):
    """
    Used when a file checksum does not match the stored value.
    """
