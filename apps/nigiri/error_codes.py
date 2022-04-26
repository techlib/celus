import typing
from enum import Enum


class ErrorCode(Enum):
    SERVICE_NOT_AVAILABLE = 1000
    SERVICE_BUSY = 1010
    PREPARING_DATA = 1011
    TOO_MANY_REQUESTS = 1020
    INSUFFICIENT_DATA = 1030
    NOT_AUTHORIZED = 2000
    NOT_AUTHORIZED_INSTITUTION = 2010
    INVALID_API_KEY = 2020
    NOT_AUTHORIZED_IP_ADDRESS = 2030
    REPORT_NOT_SUPPORTED = 3000
    REPORT_VERSION_NOT_SUPPORTED = 3010
    INVALID_DATE_ARGS = 3020
    NO_DATA_FOR_DATE_ARGS = 3030
    DATA_NOT_READY_FOR_DATE_ARGS = 3031
    NO_LONGER_AVAILABLE = 3032
    PARTIAL_DATA_RETURNED = 3040
    PARAMETER_NOT_RECOGNIZED = 3050
    INVALID_REPORT_FILTER = 3060
    INCONGRUOUS_REPORT_FILTER = 3061
    INVALID_REPORT_ATTRIBUTE = 3062
    MISSING_REPORT_FILTER = 3070
    MISSING_REPORT_ATTRIBUTE = 3071
    RETURN_DATA_LIMIT_REACHED = 3080

    def __eq__(self, o):
        if isinstance(o, int):
            return self.value == o
        else:
            return super().__eq__(o)


def error_code_to_severity(error_code: typing.Union[None, int, str]) -> str:
    if error_code is None:
        return "Error"
    try:
        error_code = int(error_code)
    except (ValueError, TypeError):
        return "Error"

    if error_code == 0:
        return "Info"
    elif 1 < error_code < 999:
        return "Warning"
    elif error_code == ErrorCode.SERVICE_NOT_AVAILABLE.value:
        return "Error"  # Fatal
    elif error_code == ErrorCode.SERVICE_BUSY.value:
        return "Error"  # Fatal
    elif error_code == ErrorCode.PREPARING_DATA.value:
        return "Warning"
    elif error_code == ErrorCode.TOO_MANY_REQUESTS.value:
        return "Error"  # Fatal
    elif error_code == ErrorCode.INSUFFICIENT_DATA.value:
        return "Error"  # Fatal
    elif error_code == ErrorCode.NOT_AUTHORIZED.value:
        return "Error"
    elif error_code == ErrorCode.NOT_AUTHORIZED_INSTITUTION.value:
        return "Error"
    elif error_code == ErrorCode.INVALID_API_KEY.value:
        return "Error"
    elif error_code == ErrorCode.NOT_AUTHORIZED_IP_ADDRESS.value:
        return "Error"
    elif error_code == ErrorCode.REPORT_NOT_SUPPORTED.value:
        return "Error"
    elif error_code == ErrorCode.REPORT_VERSION_NOT_SUPPORTED.value:
        return "Error"
    elif error_code == ErrorCode.INVALID_DATE_ARGS.value:
        return "Error"
    elif error_code == ErrorCode.NO_DATA_FOR_DATE_ARGS.value:
        return "Error"
    elif error_code == ErrorCode.DATA_NOT_READY_FOR_DATE_ARGS.value:
        return "Error"  # or Warning
    elif error_code == ErrorCode.NO_LONGER_AVAILABLE.value:
        return "Warning"
    elif error_code == ErrorCode.PARTIAL_DATA_RETURNED.value:
        return "Warning"
    elif error_code == ErrorCode.PARAMETER_NOT_RECOGNIZED.value:
        # According to standard this is supposed to be Warning
        # But full data are supposed to be returned once this status
        # occurs. So it is conveted to info.
        return "Info"
    elif error_code == ErrorCode.INVALID_REPORT_FILTER.value:
        return "Warning"  # or Error
    elif error_code == ErrorCode.INCONGRUOUS_REPORT_FILTER.value:
        # According to standard this is supposed to be Warning or Error
        # But full data are supposed to be returned once this status
        # occurs. So it is conveted to info.
        return "Info"
    elif error_code == ErrorCode.INVALID_REPORT_ATTRIBUTE.value:
        # According to standard this is supposed to be Warning or Error
        # But full data are supposed to be returned once this status
        # occurs. So it is conveted to info.
        return "Info"
    elif error_code == ErrorCode.MISSING_REPORT_FILTER.value:
        return "Error"  # or Warning
    elif error_code == ErrorCode.MISSING_REPORT_ATTRIBUTE.value:
        return "Error"  # or Warning
    elif error_code == ErrorCode.RETURN_DATA_LIMIT_REACHED.value:
        return "Warning"
    else:
        return "Error"
